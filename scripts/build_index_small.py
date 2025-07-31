#!/usr/bin/env python3
"""Build FAISS index with a very small dataset for testing."""

import sys
import gc
from pathlib import Path
from loguru import logger

# Add src to path
sys.path.append(str(Path(__file__).parent.parent))

from src.data_extraction import SFDCClient
from src.utils import TextProcessor
from src.vectorization import VectorDatabase

def main():
    """Main function to build vector index with small dataset."""
    # Configure logging
    logger.add(
        "logs/build_index_small_{time}.log",
        rotation="10 MB",
        retention="10 days",
        level="INFO"
    )
    
    logger.info("Starting FAISS index build with small dataset")
    
    try:
        # Extract only 50 cases for testing
        logger.info("Connecting to SFDC and extracting small dataset...")
        sfdc_client = SFDCClient()
        
        # Test connection first
        if not sfdc_client.test_connection():
            raise Exception("SFDC connection test failed")
        
        # Extract small dataset
        case_data = sfdc_client.get_case_data()
        
        # Limit to first 50 cases
        case_data = case_data.head(50)
        logger.info(f"Extracted {len(case_data)} cases for testing")
        
        # Initialize text processor
        logger.info("Processing text data...")
        text_processor = TextProcessor()
        processed_data = text_processor.preprocess_case_data(case_data)
        
        # Get text statistics
        stats = text_processor.get_text_stats(processed_data)
        logger.info(f"Text processing complete. Stats: {stats}")
        
        # Force garbage collection before loading model
        gc.collect()
        
        # Initialize vector database
        logger.info("Initializing vector database...")
        vector_db = VectorDatabase()
        
        # Build vector index
        logger.info("Building FAISS vector index...")
        vector_db.build_index(processed_data)
        
        # Save index
        logger.info("Saving vector index...")
        vector_db.save_index()
        
        # Get final statistics
        db_stats = vector_db.get_stats()
        logger.info(f"Index build complete! Final stats: {db_stats}")
        
        # Test search functionality
        logger.info("Testing search functionality...")
        test_queries = ["login authentication", "performance issues"]
        
        for query in test_queries:
            results = vector_db.search(query, top_k=3)
            logger.info(f"Query '{query}' returned {len(results)} results")
            if results:
                logger.info(f"  Top result: {results[0]['subject']} (score: {results[0]['similarity_score']:.3f})")
        
        logger.info("Small dataset index build completed successfully!")
        logger.info("You can now test the API with: make run-api")
        return 0
        
    except Exception as e:
        logger.error(f"Error during small index build: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return 1

if __name__ == "__main__":
    sys.exit(main())