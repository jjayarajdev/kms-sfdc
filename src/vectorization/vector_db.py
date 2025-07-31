"""FAISS-based vector database for KMS-SFDC case similarity search."""

import json
import pickle
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd
import faiss
from sentence_transformers import SentenceTransformer
from loguru import logger

from ..utils.config import config
from ..utils.backup_manager import BackupManager
from ..utils.performance_metrics import track_performance, metrics_collector


class VectorDatabase:
    """FAISS-based vector database for case similarity search."""
    
    def __init__(self):
        """Initialize vector database."""
        self.config = config.vectordb
        self.model = None
        self.index = None
        self.case_metadata = {}
        self.is_trained = False
        
        # Ensure data directory exists
        Path(self.config.index_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize backup manager
        self.backup_manager = BackupManager()
        
    def _load_model(self) -> None:
        """Load embedding model for local execution."""
        if self.model is None:
            model_name = self.config.model_name
            
            logger.info(f"Loading embedding model: {model_name}")
            
            # Determine best device based on availability and config
            device = self._get_best_device()
            logger.info(f"Using device: {device}")
            
            # Load model with optimal device
            self.model = SentenceTransformer(model_name, device=device)
                
            logger.info("Model loaded successfully for local execution")
    
    def _get_best_device(self) -> str:
        """Determine the best device for model execution."""
        import torch
        
        if not self.config.use_gpu:
            return 'cpu'
        
        # Check for MPS (Apple Silicon GPU)
        if hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
            return 'mps'
        
        # Check for CUDA
        if torch.cuda.is_available():
            return 'cuda'
        
        # Fallback to CPU
        logger.warning("GPU requested but not available, falling back to CPU")
        return 'cpu'
    
    @track_performance("create_embeddings")
    def create_embeddings(self, texts: List[str]) -> np.ndarray:
        """
        Create embeddings for list of texts using local embeddings.
        
        Args:
            texts: List of text strings to embed
            
        Returns:
            NumPy array of embeddings
        """
        self._load_model()
        
        logger.info(f"Creating embeddings for {len(texts)} texts")
        
        # Use sentence-transformers encode method with optimal device
        device = self._get_best_device()
        batch_size = min(64 if device == 'mps' else 32, len(texts))  # Larger batch for GPU
        
        embeddings = self.model.encode(
            texts,
            convert_to_numpy=True,
            show_progress_bar=len(texts) > 100,
            batch_size=batch_size,
            device=device
        )
        
        logger.info(f"Created embeddings with shape: {embeddings.shape}")
        
        return embeddings
    
    def build_index(self, case_data: pd.DataFrame) -> None:
        """
        Build production-scale FAISS index from case data.
        Optimized for 2.5M+ cases with memory-efficient processing.
        
        Args:
            case_data: DataFrame with processed case data including 'combined_text'
        """
        total_cases = len(case_data)
        logger.info(f"Building production-scale FAISS index from {total_cases} cases")
        
        if total_cases > 1000000:
            logger.info("Large dataset detected - using optimized IndexIVFPQ configuration")
        
        # Create embeddings in memory-efficient batches
        texts = case_data['combined_text'].tolist()
        embeddings = self._create_embeddings_large_scale(texts)
        
        # Normalize embeddings for cosine similarity
        faiss.normalize_L2(embeddings)
        
        # Create production-scale FAISS index
        dimension = embeddings.shape[1]
        self.index = self._create_production_index(dimension, total_cases)
        
        # Train index if required (for IVF-based indexes)
        if hasattr(self.index, 'is_trained') and not self.index.is_trained:
            logger.info("Training FAISS index...")
            training_size = min(total_cases, 1000000)  # Use up to 1M vectors for training
            self.index.train(embeddings[:training_size])
            logger.info("Index training completed")
        
        # Add embeddings to index in batches
        self._add_embeddings_batch(embeddings)
        
        # Store metadata efficiently
        self._store_metadata_batch(case_data)
        
        self.is_trained = True
        logger.info(f"Production FAISS index built successfully with {self.index.ntotal} vectors")
        
        # Log memory usage and performance metrics
        self._log_index_metrics()
    
    def _create_embeddings_large_scale(self, texts: List[str]) -> np.ndarray:
        """
        Create embeddings for large-scale data with memory management.
        
        Args:
            texts: List of text strings to embed
            
        Returns:
            NumPy array of embeddings
        """
        self._load_model()
        
        total_texts = len(texts)
        batch_size = self.config.embedding_batch_size
        all_embeddings = []
        
        logger.info(f"Creating embeddings for {total_texts} texts in batches of {batch_size}")
        
        start_time = time.time()
        
        for i in range(0, total_texts, batch_size):
            batch_texts = texts[i:i + batch_size]
            batch_start = time.time()
            
            try:
                # Use sentence-transformers encode method
                batch_embeddings = self.model.encode(
                    batch_texts,
                    convert_to_numpy=True,
                    show_progress_bar=False
                )
                
                all_embeddings.append(batch_embeddings)
                
                # Record batch metrics
                batch_time = (time.time() - batch_start) * 1000
                metrics_collector.record_batch_processing(
                    batch_size=len(batch_texts),
                    processing_time_ms=batch_time,
                    records_processed=len(batch_texts),
                    operation="embedding"
                )
                
                # Progress logging
                progress = (i + len(batch_texts)) / total_texts * 100
                logger.info(f"Embedding progress: {progress:.1f}% ({i + len(batch_texts)}/{total_texts})")
                
                # Memory cleanup for large batches
                if len(all_embeddings) >= 10:  # Combine every 10 batches
                    combined = np.vstack(all_embeddings)
                    all_embeddings = [combined]
                
            except Exception as e:
                logger.error(f"Error processing batch {i}-{i+len(batch_texts)}: {e}")
                raise
        
        # Combine all embeddings
        embeddings = np.vstack(all_embeddings)
        
        total_time = (time.time() - start_time) * 1000
        metrics_collector.record_operation("embeddings_large_scale", total_time)
        
        logger.info(f"Created embeddings with shape: {embeddings.shape}")
        
        return embeddings
    
    def _create_production_index(self, dimension: int, dataset_size: int) -> faiss.Index:
        """
        Create production-optimized FAISS index based on dataset size.
        
        Args:
            dimension: Embedding dimension
            dataset_size: Number of vectors to index
            
        Returns:
            Configured FAISS index
        """
        if self.config.faiss_index_type == "IndexIVFPQ" and dataset_size > 100000:
            # Large-scale index with compression
            nlist = getattr(self.config, 'nlist', 4096)
            m = getattr(self.config, 'm', 64)
            nbits = getattr(self.config, 'nbits', 8)
            
            # Create quantizer
            quantizer = faiss.IndexFlatIP(dimension)
            
            # Create IVF-PQ index
            index = faiss.IndexIVFPQ(quantizer, dimension, nlist, m, nbits)
            
            # Set search parameters
            index.nprobe = getattr(self.config, 'search_nprobe', 128)
            
            logger.info(f"Created IndexIVFPQ: nlist={nlist}, m={m}, nbits={nbits}, nprobe={index.nprobe}")
            
        elif self.config.faiss_index_type == "IndexHNSWFlat" or dataset_size > 50000:
            # HNSW index for medium to large datasets
            index = faiss.IndexHNSWFlat(dimension, 32)
            index.hnsw.efConstruction = 200
            index.hnsw.efSearch = 128
            
            logger.info(f"Created IndexHNSWFlat for {dataset_size} vectors")
            
        else:
            # Flat index for smaller datasets
            index = faiss.IndexFlatIP(dimension)
            logger.info(f"Created IndexFlatIP for {dataset_size} vectors")
        
        return index
    
    def _add_embeddings_batch(self, embeddings: np.ndarray) -> None:
        """
        Add embeddings to index in memory-efficient batches.
        
        Args:
            embeddings: Embeddings array to add
        """
        total_vectors = embeddings.shape[0]
        batch_size = self.config.indexing_batch_size
        
        logger.info(f"Adding {total_vectors} vectors to index in batches of {batch_size}")
        
        for i in range(0, total_vectors, batch_size):
            end_idx = min(i + batch_size, total_vectors)
            batch = embeddings[i:end_idx]
            
            self.index.add(batch)
            
            progress = end_idx / total_vectors * 100
            logger.info(f"Indexing progress: {progress:.1f}% ({end_idx}/{total_vectors})")
    
    def _store_metadata_batch(self, case_data: pd.DataFrame) -> None:
        """
        Store case metadata efficiently for large datasets.
        
        Args:
            case_data: DataFrame with case data
        """
        logger.info("Storing case metadata...")
        
        self.case_metadata = {}
        
        # Process in chunks to manage memory
        chunk_size = 50000
        for start_idx in range(0, len(case_data), chunk_size):
            end_idx = min(start_idx + chunk_size, len(case_data))
            chunk = case_data.iloc[start_idx:end_idx]
            
            for idx, (_, row) in enumerate(chunk.iterrows(), start=start_idx):
                self.case_metadata[idx] = {
                    'case_id': row.get('Id', ''),
                    'case_number': row.get('Case_Number', ''),
                    'subject_description': row.get('Subject_Description', ''),
                    'description_description': row.get('Description_Description', ''),
                    'issue_plain_text': row.get('Issue_Plain_Text', ''),
                    'cause_plain_text': row.get('Cause_Plain_Text', ''),
                    'resolution_plain_text': row.get('Resolution_Plain_Text', ''),
                    'status_text': row.get('Status_Text', ''),
                    'textbody': row.get('TextBody', ''),
                    'created_date': str(row.get('CreatedDate', '')),
                    'combined_text': row.get('combined_text', '')[:500]  # Truncate for storage
                }
            
            logger.info(f"Stored metadata for {end_idx}/{len(case_data)} cases")
    
    def _log_index_metrics(self) -> None:
        """Log index performance metrics."""
        try:
            import psutil
            import os
            
            # Memory usage
            process = psutil.Process(os.getpid())
            memory_mb = process.memory_info().rss / 1024 / 1024
            
            # Index statistics
            stats = {
                'total_vectors': self.index.ntotal,
                'index_type': type(self.index).__name__,
                'memory_usage_mb': f"{memory_mb:.1f}",
                'vectors_per_mb': f"{self.index.ntotal / memory_mb:.1f}" if memory_mb > 0 else "N/A"
            }
            
            logger.info(f"Index metrics: {stats}")
            
        except ImportError:
            logger.info("psutil not available - skipping memory metrics")
    
    @track_performance("vector_search")
    def search(self, query_text: str, top_k: int = None, 
               similarity_threshold: float = None) -> List[Dict]:
        """
        Search for similar cases using query text.
        
        Args:
            query_text: Text to search for similar cases
            top_k: Number of results to return (defaults to config value)
            similarity_threshold: Minimum similarity score (defaults to config value)
            
        Returns:
            List of similar cases with metadata and scores
        """
        if not self.is_trained or self.index is None:
            raise ValueError("Index not built. Call build_index() first.")
        
        if top_k is None:
            top_k = config.search.default_top_k
        if similarity_threshold is None:
            similarity_threshold = config.search.similarity_threshold
        
        logger.debug(f"Searching for similar cases: '{query_text[:100]}...'")
        
        # Create embedding for query
        query_embedding = self.create_embeddings([query_text])
        faiss.normalize_L2(query_embedding)
        
        # Search index
        scores, indices = self.index.search(query_embedding, min(top_k, self.index.ntotal))
        
        # Format results
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if score >= similarity_threshold:
                case_info = self.case_metadata.get(idx, {})
                results.append({
                    'similarity_score': float(score),
                    'case_id': case_info.get('case_id', ''),
                    'case_number': case_info.get('case_number', ''),
                    'subject_description': case_info.get('subject_description', ''),
                    'description_description': case_info.get('description_description', ''),
                    'issue_plain_text': case_info.get('issue_plain_text', ''),
                    'cause_plain_text': case_info.get('cause_plain_text', ''),
                    'resolution_plain_text': case_info.get('resolution_plain_text', ''),
                    'status_text': case_info.get('status_text', ''),
                    'textbody': case_info.get('textbody', ''),
                    'created_date': case_info.get('created_date', ''),
                    'preview_text': case_info.get('combined_text', '')
                })
        
        logger.info(f"Found {len(results)} similar cases above threshold {similarity_threshold}")
        return results
    
    def save_index(self, index_path: str = None, metadata_path: str = None,
                   create_backup: bool = True, backup_description: str = "") -> None:
        """
        Save FAISS index and metadata to disk with optional backup.
        
        Args:
            index_path: Path to save FAISS index (defaults to config path)
            metadata_path: Path to save metadata (defaults to config path)
            create_backup: Whether to create a backup before saving
            backup_description: Description for the backup
        """
        if not self.is_trained:
            raise ValueError("No index to save. Build index first.")
        
        if index_path is None:
            index_path = self.config.index_path
        if metadata_path is None:
            metadata_path = self.config.metadata_path
        
        # Create directories if they don't exist
        Path(index_path).parent.mkdir(parents=True, exist_ok=True)
        Path(metadata_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Create backup if requested and files exist
        if create_backup and (Path(index_path).exists() or Path(metadata_path).exists()):
            try:
                backup_id = self.backup_manager.create_backup(
                    index_path, metadata_path, backup_description or "Pre-save backup"
                )
                logger.info(f"Created backup {backup_id} before saving")
            except Exception as e:
                logger.warning(f"Backup creation failed: {e}")
        
        # Save FAISS index
        faiss.write_index(self.index, index_path)
        logger.info(f"FAISS index saved to {index_path}")
        
        # Save metadata
        with open(metadata_path, 'w') as f:
            json.dump(self.case_metadata, f, indent=2)
        logger.info(f"Metadata saved to {metadata_path}")
    
    def load_index(self, index_path: str = None, metadata_path: str = None,
                   use_memory_mapping: bool = None) -> None:
        """
        Load FAISS index and metadata from disk.
        
        Args:
            index_path: Path to FAISS index file (defaults to config path)
            metadata_path: Path to metadata file (defaults to config path)
            use_memory_mapping: Whether to use memory mapping for large indexes
        """
        if index_path is None:
            index_path = self.config.index_path
        if metadata_path is None:
            metadata_path = self.config.metadata_path
        if use_memory_mapping is None:
            use_memory_mapping = self.config.memory_mapping
        
        if not Path(index_path).exists():
            raise FileNotFoundError(f"Index file not found: {index_path}")
        if not Path(metadata_path).exists():
            raise FileNotFoundError(f"Metadata file not found: {metadata_path}")
        
        # Check index size for memory mapping decision
        index_size_mb = Path(index_path).stat().st_size / (1024 * 1024)
        
        # Load FAISS index with memory mapping for large indexes
        if use_memory_mapping and index_size_mb > 1000:  # Use memory mapping for > 1GB indexes
            logger.info(f"Loading large index ({index_size_mb:.1f}MB) with memory mapping")
            self.index = faiss.read_index(index_path, faiss.IO_FLAG_MMAP)
        else:
            self.index = faiss.read_index(index_path)
        
        logger.info(f"FAISS index loaded from {index_path} (size: {index_size_mb:.1f}MB)")
        
        # Load metadata
        with open(metadata_path, 'r') as f:
            metadata_dict = json.load(f)
            # Convert string keys back to integers
            self.case_metadata = {int(k): v for k, v in metadata_dict.items()}
        logger.info(f"Metadata loaded from {metadata_path}")
        
        # Load model for future searches
        self._load_model()
        
        self.is_trained = True
        logger.info(f"Vector database ready with {self.index.ntotal} vectors")
    
    def get_stats(self) -> Dict:
        """Get statistics about the vector database."""
        stats = {
            'is_trained': self.is_trained,
            'total_vectors': self.index.ntotal if self.index else 0,
            'dimension': self.index.d if self.index else 0,
            'index_type': self.config.faiss_index_type,
            'model_name': self.config.model_name,
            'metadata_count': len(self.case_metadata)
        }
        
        return stats
    
    def update_index_incremental(self, new_case_data: pd.DataFrame) -> None:
        """
        Update existing index with new case data using incremental approach.
        Optimized for daily updates of ~2,740 cases (1M annually).
        
        Args:
            new_case_data: DataFrame with new case data to add
        """
        if not self.is_trained:
            logger.warning("No existing index. Building new index instead.")
            self.build_index(new_case_data)
            return
        
        new_case_count = len(new_case_data)
        logger.info(f"Performing incremental update with {new_case_count} new cases")
        
        # Check if we should do full rebuild
        current_total = self.index.ntotal
        incremental_threshold = getattr(self.config, 'incremental_merge_threshold', 100000)
        
        if current_total > incremental_threshold and new_case_count > incremental_threshold // 10:
            logger.info("Large incremental update detected - considering full rebuild")
            # Could implement smart rebuild decision here
        
        # Process new data in batches for memory efficiency
        batch_size = getattr(self.config, 'daily_update_batch_size', 10000)
        
        for start_idx in range(0, new_case_count, batch_size):
            end_idx = min(start_idx + batch_size, new_case_count)
            batch_data = new_case_data.iloc[start_idx:end_idx]
            
            logger.info(f"Processing incremental batch {start_idx}-{end_idx}")
            
            # Create embeddings for batch
            texts = batch_data['combined_text'].tolist()
            embeddings = self._create_embeddings_large_scale(texts)
            faiss.normalize_L2(embeddings)
            
            # Add to existing index
            metadata_start_idx = self.index.ntotal
            self.index.add(embeddings)
            
            # Update metadata
            for idx, (_, row) in enumerate(batch_data.iterrows()):
                metadata_idx = metadata_start_idx + idx
                self.case_metadata[metadata_idx] = {
                    'case_id': row.get('Id', ''),
                    'case_number': row.get('Case_Number', ''),
                    'subject_description': row.get('Subject_Description', ''),
                    'description_description': row.get('Description_Description', ''),
                    'issue_plain_text': row.get('Issue_Plain_Text', ''),
                    'cause_plain_text': row.get('Cause_Plain_Text', ''),
                    'resolution_plain_text': row.get('Resolution_Plain_Text', ''),
                    'status_text': row.get('Status_Text', ''),
                    'textbody': row.get('TextBody', ''),
                    'created_date': str(row.get('CreatedDate', '')),
                    'combined_text': row.get('combined_text', '')[:500]
                }
            
            logger.info(f"Added batch to index. Current total: {self.index.ntotal}")
        
        logger.info(f"Incremental update completed. Total vectors: {self.index.ntotal}")
        
        # Save updated index
        self.save_index()
    
    def optimize_index_for_search(self) -> None:
        """
        Optimize index for search performance after incremental updates.
        """
        if not self.is_trained:
            logger.warning("No index to optimize")
            return
        
        logger.info("Optimizing index for search performance...")
        
        # For IVF indexes, we might want to retrain centroids periodically
        if hasattr(self.index, 'quantizer') and hasattr(self.index, 'is_trained'):
            total_vectors = self.index.ntotal
            
            # Retrain if we have significantly more data
            if total_vectors > 2000000:  # Retrain after 2M vectors
                logger.info("Large index detected - retraining centroids for optimal performance")
                
                # This is a placeholder - in production, you'd extract vectors and retrain
                # For now, we'll just log the recommendation
                logger.info("Consider full index rebuild for optimal search performance")
        
        logger.info("Index optimization completed")
    
    def get_index_health_metrics(self) -> Dict:
        """
        Get comprehensive health metrics for large-scale index monitoring.
        
        Returns:
            Dictionary with detailed health metrics
        """
        if not self.is_trained:
            return {'status': 'not_trained', 'health': 'unhealthy'}
        
        try:
            # Basic stats
            total_vectors = self.index.ntotal
            index_type = type(self.index).__name__
            
            # Memory estimates
            estimated_memory_mb = 0
            if hasattr(self.index, 'd'):
                dimension = self.index.d
                if index_type == 'IndexFlatIP':
                    estimated_memory_mb = (total_vectors * dimension * 4) / (1024 * 1024)  # float32
                elif index_type == 'IndexIVFPQ':
                    # Rough estimate for compressed index
                    estimated_memory_mb = (total_vectors * getattr(self.config, 'm', 64) * getattr(self.config, 'nbits', 8) / 8) / (1024 * 1024)
            
            # Performance indicators
            metrics = {
                'status': 'healthy',
                'total_vectors': total_vectors,
                'index_type': index_type,
                'estimated_memory_mb': f"{estimated_memory_mb:.1f}",
                'metadata_count': len(self.case_metadata),
                'dimension': getattr(self.index, 'd', 'unknown'),
                'scale_category': self._get_scale_category(total_vectors),
                'recommended_actions': self._get_optimization_recommendations(total_vectors, index_type)
            }
            
            # Add index-specific metrics
            if index_type == 'IndexIVFPQ':
                metrics.update({
                    'nlist': getattr(self.index, 'nlist', 'unknown'),
                    'nprobe': getattr(self.index, 'nprobe', 'unknown'),
                    'is_trained': getattr(self.index, 'is_trained', False)
                })
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error getting health metrics: {e}")
            return {'status': 'error', 'health': 'unhealthy', 'error': str(e)}
    
    def _get_scale_category(self, total_vectors: int) -> str:
        """Categorize the scale of the dataset."""
        if total_vectors < 100000:
            return 'small'
        elif total_vectors < 1000000:
            return 'medium'
        elif total_vectors < 5000000:
            return 'large'
        else:
            return 'extra_large'
    
    def _get_optimization_recommendations(self, total_vectors: int, index_type: str) -> List[str]:
        """Get optimization recommendations based on current state."""
        recommendations = []
        
        if total_vectors > 2500000 and index_type != 'IndexIVFPQ':
            recommendations.append("Consider migrating to IndexIVFPQ for better memory efficiency")
        
        if total_vectors > 5000000:
            recommendations.append("Consider GPU acceleration for faster search")
            recommendations.append("Consider index sharding for distributed processing")
        
        if len(self.case_metadata) != total_vectors:
            recommendations.append("Metadata count mismatch - recommend index verification")
        
        return recommendations
    
    def update_index(self, new_case_data: pd.DataFrame) -> None:
        """
        Legacy update method - redirects to incremental update.
        
        Args:
            new_case_data: DataFrame with new case data to add
        """
        logger.info("Redirecting to incremental update method")
        self.update_index_incremental(new_case_data)