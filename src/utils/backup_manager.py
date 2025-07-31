"""Backup and versioning utilities for KMS-SFDC Vector Database."""

import os
import shutil
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from loguru import logger

from .config import config


class BackupManager:
    """Manages backup and versioning of FAISS indexes and metadata."""
    
    def __init__(self, backup_dir: str = "data/backups"):
        """
        Initialize backup manager.
        
        Args:
            backup_dir: Directory to store backups
        """
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Backup configuration
        self.max_backups = 5  # Keep last 5 backups
        self.backup_metadata_file = self.backup_dir / "backup_metadata.json"
        
        # Load existing backup metadata
        self.backup_metadata = self._load_backup_metadata()
    
    def create_backup(self, index_path: str, metadata_path: str, 
                     description: str = "") -> str:
        """
        Create a backup of the current index and metadata.
        
        Args:
            index_path: Path to FAISS index file
            metadata_path: Path to metadata JSON file
            description: Optional description of the backup
            
        Returns:
            Backup ID (timestamp-based)
        """
        # Generate backup ID
        backup_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_subdir = self.backup_dir / backup_id
        backup_subdir.mkdir(exist_ok=True)
        
        logger.info(f"Creating backup {backup_id}")
        
        try:
            # Copy index file
            if Path(index_path).exists():
                index_backup = backup_subdir / "faiss_index.bin"
                shutil.copy2(index_path, index_backup)
                logger.info(f"Backed up index to {index_backup}")
            else:
                logger.warning(f"Index file not found: {index_path}")
            
            # Copy metadata file
            if Path(metadata_path).exists():
                metadata_backup = backup_subdir / "case_metadata.json"
                shutil.copy2(metadata_path, metadata_backup)
                logger.info(f"Backed up metadata to {metadata_backup}")
            else:
                logger.warning(f"Metadata file not found: {metadata_path}")
            
            # Create backup info
            backup_info = {
                "id": backup_id,
                "timestamp": datetime.now().isoformat(),
                "description": description,
                "index_size": os.path.getsize(index_path) if Path(index_path).exists() else 0,
                "metadata_size": os.path.getsize(metadata_path) if Path(metadata_path).exists() else 0,
                "files": {
                    "index": str(backup_subdir / "faiss_index.bin"),
                    "metadata": str(backup_subdir / "case_metadata.json")
                }
            }
            
            # Save backup info
            with open(backup_subdir / "backup_info.json", 'w') as f:
                json.dump(backup_info, f, indent=2)
            
            # Update backup metadata
            self.backup_metadata[backup_id] = backup_info
            self._save_backup_metadata()
            
            # Clean up old backups
            self._cleanup_old_backups()
            
            logger.info(f"Backup {backup_id} created successfully")
            return backup_id
            
        except Exception as e:
            logger.error(f"Backup creation failed: {e}")
            # Clean up partial backup
            if backup_subdir.exists():
                shutil.rmtree(backup_subdir)
            raise
    
    def restore_backup(self, backup_id: str, index_path: str, 
                      metadata_path: str) -> bool:
        """
        Restore a backup to the specified paths.
        
        Args:
            backup_id: ID of backup to restore
            index_path: Destination path for FAISS index
            metadata_path: Destination path for metadata
            
        Returns:
            True if successful, False otherwise
        """
        if backup_id not in self.backup_metadata:
            logger.error(f"Backup {backup_id} not found")
            return False
        
        backup_info = self.backup_metadata[backup_id]
        logger.info(f"Restoring backup {backup_id} from {backup_info['timestamp']}")
        
        try:
            # Create current backup before restoring
            if Path(index_path).exists() or Path(metadata_path).exists():
                logger.info("Creating backup of current state before restore")
                self.create_backup(index_path, metadata_path, 
                                 description=f"Pre-restore backup before restoring {backup_id}")
            
            # Restore index
            backup_index = backup_info["files"]["index"]
            if Path(backup_index).exists():
                shutil.copy2(backup_index, index_path)
                logger.info(f"Restored index from {backup_index}")
            
            # Restore metadata
            backup_metadata = backup_info["files"]["metadata"]
            if Path(backup_metadata).exists():
                shutil.copy2(backup_metadata, metadata_path)
                logger.info(f"Restored metadata from {backup_metadata}")
            
            logger.info(f"Backup {backup_id} restored successfully")
            return True
            
        except Exception as e:
            logger.error(f"Restore failed: {e}")
            return False
    
    def list_backups(self) -> List[Dict]:
        """
        List all available backups.
        
        Returns:
            List of backup information dictionaries
        """
        backups = []
        
        for backup_id, info in sorted(self.backup_metadata.items(), 
                                     key=lambda x: x[1]['timestamp'], 
                                     reverse=True):
            backup_dir = self.backup_dir / backup_id
            if backup_dir.exists():
                backups.append({
                    "id": backup_id,
                    "timestamp": info["timestamp"],
                    "description": info.get("description", ""),
                    "index_size_mb": info.get("index_size", 0) / (1024 * 1024),
                    "metadata_size_mb": info.get("metadata_size", 0) / (1024 * 1024)
                })
        
        return backups
    
    def delete_backup(self, backup_id: str) -> bool:
        """
        Delete a specific backup.
        
        Args:
            backup_id: ID of backup to delete
            
        Returns:
            True if successful, False otherwise
        """
        if backup_id not in self.backup_metadata:
            logger.error(f"Backup {backup_id} not found")
            return False
        
        backup_dir = self.backup_dir / backup_id
        
        try:
            if backup_dir.exists():
                shutil.rmtree(backup_dir)
            
            del self.backup_metadata[backup_id]
            self._save_backup_metadata()
            
            logger.info(f"Backup {backup_id} deleted")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete backup: {e}")
            return False
    
    def get_backup_info(self, backup_id: str) -> Optional[Dict]:
        """
        Get detailed information about a specific backup.
        
        Args:
            backup_id: ID of backup
            
        Returns:
            Backup information dictionary or None
        """
        if backup_id not in self.backup_metadata:
            return None
        
        info = self.backup_metadata[backup_id].copy()
        backup_dir = self.backup_dir / backup_id
        
        # Add current file existence status
        info["files_exist"] = {
            "index": Path(info["files"]["index"]).exists(),
            "metadata": Path(info["files"]["metadata"]).exists()
        }
        
        return info
    
    def _load_backup_metadata(self) -> Dict:
        """Load backup metadata from disk."""
        if self.backup_metadata_file.exists():
            try:
                with open(self.backup_metadata_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load backup metadata: {e}")
        
        return {}
    
    def _save_backup_metadata(self):
        """Save backup metadata to disk."""
        try:
            with open(self.backup_metadata_file, 'w') as f:
                json.dump(self.backup_metadata, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save backup metadata: {e}")
    
    def _cleanup_old_backups(self):
        """Remove old backups beyond max_backups limit."""
        if len(self.backup_metadata) <= self.max_backups:
            return
        
        # Sort by timestamp and get oldest backups to remove
        sorted_backups = sorted(self.backup_metadata.items(), 
                               key=lambda x: x[1]['timestamp'])
        
        backups_to_remove = len(self.backup_metadata) - self.max_backups
        
        for backup_id, _ in sorted_backups[:backups_to_remove]:
            logger.info(f"Removing old backup {backup_id}")
            self.delete_backup(backup_id)
    
    def create_versioned_backup(self, index_path: str, metadata_path: str,
                               version: str, changelog: str = "") -> str:
        """
        Create a versioned backup with semantic versioning.
        
        Args:
            index_path: Path to FAISS index
            metadata_path: Path to metadata
            version: Semantic version (e.g., "1.0.0")
            changelog: Description of changes
            
        Returns:
            Backup ID
        """
        description = f"Version {version}"
        if changelog:
            description += f": {changelog}"
        
        backup_id = self.create_backup(index_path, metadata_path, description)
        
        # Add version info to backup metadata
        self.backup_metadata[backup_id]["version"] = version
        self.backup_metadata[backup_id]["changelog"] = changelog
        self._save_backup_metadata()
        
        return backup_id
    
    def get_latest_version(self) -> Optional[Tuple[str, str]]:
        """
        Get the latest versioned backup.
        
        Returns:
            Tuple of (backup_id, version) or None
        """
        versioned_backups = [
            (bid, info) for bid, info in self.backup_metadata.items()
            if "version" in info
        ]
        
        if not versioned_backups:
            return None
        
        # Sort by timestamp to get latest
        latest = max(versioned_backups, key=lambda x: x[1]["timestamp"])
        return latest[0], latest[1]["version"]