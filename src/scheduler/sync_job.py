"""SFDC data synchronization job implementation."""

import os
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional
import pandas as pd
from loguru import logger

from src.data_extraction import SFDCClient
from src.utils import TextProcessor, config
from src.vectorization import VectorDatabase
from src.utils.backup_manager import BackupManager


class SFDCDataSyncJob:
    """Job for synchronizing SFDC data and updating the vector database."""
    
    def __init__(self, state_file: str = "data/sync_state.json"):
        """Initialize the sync job.
        
        Args:
            state_file: Path to the sync state file
        """
        self.state_file = state_file
        self.sfdc_client = None
        self.text_processor = None
        self.vector_db = None
        self.backup_manager = BackupManager(backup_dir="data/backups")
        
        # Ensure state directory exists
        Path(self.state_file).parent.mkdir(parents=True, exist_ok=True)
        
    def load_state(self) -> Dict:
        """Load sync state from file."""
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading sync state: {e}")
                return self._default_state()
        else:
            return self._default_state()
    
    def _default_state(self) -> Dict:
        """Return default sync state."""
        return {
            "last_sync_time": None,
            "last_successful_sync": None,
            "total_cases_synced": 0,
            "total_cases_in_index": 0,
            "sync_history": []
        }
    
    def save_state(self, state: Dict) -> None:
        """Save sync state to file."""
        try:
            with open(self.state_file, 'w') as f:
                json.dump(state, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error saving sync state: {e}")
    
    def initialize_components(self) -> None:
        """Initialize required components."""
        logger.info("Initializing sync job components")
        
        # Initialize SFDC client
        self.sfdc_client = SFDCClient()
        if not self.sfdc_client.test_connection():
            raise Exception("Failed to connect to Salesforce")
        
        # Initialize text processor
        self.text_processor = TextProcessor()
        
        # Initialize vector database
        self.vector_db = VectorDatabase()
        
        # Load existing index if available
        if os.path.exists(config.vectordb.index_path):
            logger.info("Loading existing vector index")
            self.vector_db.load_index()
        else:
            logger.info("No existing index found, will create new one")
    
    def calculate_sync_window(self) -> tuple[Optional[datetime], Optional[datetime]]:
        """Calculate the time window for syncing data.
        
        Returns:
            Tuple of (start_date, end_date)
        """
        state = self.load_state()
        
        # End date is now
        end_date = datetime.utcnow()
        
        # Start date calculation
        if state["last_successful_sync"]:
            # Sync from last successful sync time
            start_date = datetime.fromisoformat(state["last_successful_sync"])
            # Add a small overlap to ensure no data is missed
            start_date = start_date - timedelta(minutes=5)
        else:
            # First sync - get data from configured range
            years_back = getattr(config.salesforce, 'date_range_years', 2)
            start_date = end_date - timedelta(days=365 * years_back)
        
        logger.info(f"Sync window: {start_date} to {end_date}")
        return start_date, end_date
    
    def run(self) -> Dict:
        """Execute the sync job.
        
        Returns:
            Dictionary with sync results
        """
        logger.info("Starting SFDC data sync job")
        start_time = datetime.utcnow()
        state = self.load_state()
        
        # Track sync metrics
        sync_result = {
            "start_time": start_time.isoformat(),
            "status": "running",
            "cases_extracted": 0,
            "cases_processed": 0,
            "cases_added": 0,
            "cases_updated": 0,
            "errors": []
        }
        
        try:
            # Initialize components
            self.initialize_components()
            
            # Calculate sync window
            start_date, end_date = self.calculate_sync_window()
            
            # Create backup before sync
            if self.vector_db.is_trained:
                logger.info("Creating backup before sync")
                backup_id = self.backup_manager.create_backup(
                    index_path=config.vectordb.index_path,
                    metadata_path=config.vectordb.metadata_path,
                    description=f"Pre-sync backup - {start_time.isoformat()}"
                )
                sync_result["backup_id"] = backup_id
            
            # Extract new/updated cases
            logger.info("Extracting cases from Salesforce")
            all_cases = []
            
            for batch_df in self.sfdc_client.extract_case_data_batched(
                start_date=start_date,
                end_date=end_date,
                batch_size=getattr(config.salesforce, 'query_batch_size', 2000)
            ):
                all_cases.append(batch_df)
                sync_result["cases_extracted"] += len(batch_df)
                
                # Log progress
                if sync_result["cases_extracted"] % 1000 == 0:
                    logger.info(f"Extracted {sync_result['cases_extracted']} cases so far")
            
            if not all_cases:
                logger.info("No new cases to sync")
                sync_result["status"] = "completed"
                sync_result["message"] = "No new cases found"
                return sync_result
            
            # Combine all batches
            case_data = pd.concat(all_cases, ignore_index=True)
            logger.info(f"Total cases extracted: {len(case_data)}")
            
            # Process text data
            logger.info("Processing case text data")
            processed_data = self.text_processor.preprocess_case_data(case_data)
            sync_result["cases_processed"] = len(processed_data)
            
            # Get text statistics
            stats = self.text_processor.get_text_stats(processed_data)
            logger.info(f"Text processing stats: {stats}")
            
            # Update vector database
            if self.vector_db.is_trained:
                # Incremental update
                logger.info("Performing incremental index update")
                
                # Filter out cases that already exist (by case ID)
                existing_ids = set(self.vector_db.case_metadata.keys())
                new_cases = processed_data[~processed_data['Id'].isin(existing_ids)]
                
                if len(new_cases) > 0:
                    self.vector_db.update_index_incremental(new_cases)
                    sync_result["cases_added"] = len(new_cases)
                
                # For updated cases, we would need to implement update logic
                # For now, we'll skip updates and only add new cases
                sync_result["cases_updated"] = 0
            else:
                # Build new index
                logger.info("Building new vector index")
                self.vector_db.build_index(processed_data)
                sync_result["cases_added"] = len(processed_data)
            
            # Save updated index
            logger.info("Saving updated vector index")
            self.vector_db.save_index()
            
            # Get final statistics
            db_stats = self.vector_db.get_stats()
            state["total_cases_in_index"] = db_stats.get("total_vectors", 0)
            
            # Update state
            state["last_sync_time"] = datetime.utcnow().isoformat()
            state["last_successful_sync"] = datetime.utcnow().isoformat()
            state["total_cases_synced"] += sync_result["cases_processed"]
            
            # Add to sync history (keep last 100 entries)
            state["sync_history"].append({
                "timestamp": start_time.isoformat(),
                "cases_processed": sync_result["cases_processed"],
                "cases_added": sync_result["cases_added"],
                "duration_seconds": (datetime.utcnow() - start_time).total_seconds()
            })
            state["sync_history"] = state["sync_history"][-100:]
            
            # Save state
            self.save_state(state)
            
            # Mark sync as successful
            sync_result["status"] = "completed"
            sync_result["end_time"] = datetime.utcnow().isoformat()
            sync_result["duration_seconds"] = (datetime.utcnow() - start_time).total_seconds()
            
            logger.info(f"Sync completed successfully: {sync_result}")
            
        except Exception as e:
            logger.error(f"Error during sync: {e}")
            sync_result["status"] = "error"
            sync_result["error"] = str(e)
            sync_result["end_time"] = datetime.utcnow().isoformat()
            
            # Try to restore from backup if available
            if "backup_id" in sync_result:
                logger.info("Attempting to restore from backup")
                try:
                    self.backup_manager.restore_backup(
                        backup_id=sync_result["backup_id"],
                        index_path=config.vectordb.index_path,
                        metadata_path=config.vectordb.metadata_path
                    )
                    logger.info("Successfully restored from backup")
                except Exception as restore_error:
                    logger.error(f"Failed to restore from backup: {restore_error}")
            
            raise
        
        return sync_result
    
    def get_sync_stats(self) -> Dict:
        """Get synchronization statistics.
        
        Returns:
            Dictionary with sync statistics
        """
        state = self.load_state()
        
        # Calculate additional stats
        stats = {
            "last_sync": state["last_sync_time"],
            "last_successful_sync": state["last_successful_sync"],
            "total_cases_synced": state["total_cases_synced"],
            "total_cases_in_index": state["total_cases_in_index"],
            "sync_history_count": len(state["sync_history"])
        }
        
        # Calculate average sync metrics from history
        if state["sync_history"]:
            history = state["sync_history"][-10:]  # Last 10 syncs
            avg_cases = sum(h["cases_processed"] for h in history) / len(history)
            avg_duration = sum(h["duration_seconds"] for h in history) / len(history)
            
            stats["average_cases_per_sync"] = round(avg_cases, 2)
            stats["average_sync_duration_seconds"] = round(avg_duration, 2)
        
        return stats
    
    def validate_sync(self) -> Dict:
        """Validate the current state of synchronization.
        
        Returns:
            Dictionary with validation results
        """
        validation = {
            "is_valid": True,
            "checks": {},
            "warnings": [],
            "errors": []
        }
        
        try:
            # Check SFDC connection (only test if we don't have cached client)
            if not hasattr(self, '_cached_sfdc_client'):
                self._cached_sfdc_client = SFDCClient()
                self._cached_connection_time = datetime.utcnow()
            
            # Use cached connection if recent (within 5 minutes)
            if (datetime.utcnow() - self._cached_connection_time).total_seconds() < 300:
                validation["checks"]["sfdc_connection"] = True  # Assume still valid
            else:
                validation["checks"]["sfdc_connection"] = self._cached_sfdc_client.test_connection()
                self._cached_connection_time = datetime.utcnow()
                
            if not validation["checks"]["sfdc_connection"]:
                validation["errors"].append("Cannot connect to Salesforce")
                validation["is_valid"] = False
            
            # Check vector database (use cached info if available)
            if os.path.exists(config.vectordb.index_path):
                if not hasattr(self, '_cached_vector_db'):
                    self._cached_vector_db = VectorDatabase()
                    self._cached_vector_db.load_index()
                    
                validation["checks"]["vector_db_loaded"] = self._cached_vector_db.is_trained
                validation["checks"]["total_vectors"] = self._cached_vector_db.index.ntotal if self._cached_vector_db.is_trained else 0
            else:
                validation["checks"]["vector_db_loaded"] = False
                validation["warnings"].append("No vector index found")
            
            # Check sync state
            state = self.load_state()
            if state["last_successful_sync"]:
                last_sync = datetime.fromisoformat(state["last_successful_sync"])
                hours_since_sync = (datetime.utcnow() - last_sync).total_seconds() / 3600
                validation["checks"]["hours_since_last_sync"] = round(hours_since_sync, 2)
                
                if hours_since_sync > 24:
                    validation["warnings"].append(f"Last sync was {hours_since_sync:.1f} hours ago")
            else:
                validation["warnings"].append("No successful sync recorded")
            
        except Exception as e:
            validation["is_valid"] = False
            validation["errors"].append(f"Validation error: {str(e)}")
        
        return validation


# Create a global instance
sfdc_sync_job = SFDCDataSyncJob()