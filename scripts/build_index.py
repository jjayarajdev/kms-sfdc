#!/usr/bin/env python3
"""Script to build initial FAISS index from SFDC case data."""

import sys
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from loguru import logger

# Add src to path
sys.path.append(str(Path(__file__).parent.parent))

from src.data_extraction import SFDCClient
from src.utils import TextProcessor, config
from src.vectorization import VectorDatabase


def main():
    """Main function to build vector index."""
    parser = argparse.ArgumentParser(description="Build FAISS index from SFDC case data")
    parser.add_argument("--start-date", type=str, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end-date", type=str, help="End date (YYYY-MM-DD)")
    parser.add_argument("--max-records", type=int, help="Maximum number of records to process")
    parser.add_argument("--batch-size", type=int, default=5000, help="Batch size for processing")
    parser.add_argument("--output-dir", type=str, help="Output directory for index files")
    
    args = parser.parse_args()
    
    # Configure logging
    logger.add(
        "logs/build_index_{time}.log",
        rotation="10 MB",
        retention="10 days",
        level="INFO"
    )
    
    logger.info("Starting FAISS index build process")
    
    try:
        # Parse dates
        start_date = None
        end_date = None
        
        if args.start_date:
            start_date = datetime.strptime(args.start_date, "%Y-%m-%d")
        if args.end_date:
            end_date = datetime.strptime(args.end_date, "%Y-%m-%d")
        
        # Initialize components
        logger.info("Initializing SFDC client...")
        sfdc_client = SFDCClient()
        
        # Test connection
        if not sfdc_client.test_connection():
            logger.error("SFDC connection test failed")
            return 1
        
        logger.info("Initializing text processor...")
        text_processor = TextProcessor()
        
        logger.info("Initializing vector database...")
        vector_db = VectorDatabase()
        
        # Extract case data
        logger.info("Extracting case data from Salesforce...")
        
        if args.batch_size and args.batch_size < 10000:
            # Use batch processing for large datasets
            all_data = []
            batch_count = 0
            
            for batch_df in sfdc_client.get_case_data_batch(start_date, end_date):
                batch_count += 1
                logger.info(f"Processing batch {batch_count} with {len(batch_df)} records")
                
                # Process batch
                processed_batch = text_processor.preprocess_case_data(batch_df)
                all_data.append(processed_batch)
                
                # Stop if max records reached
                if args.max_records and sum(len(df) for df in all_data) >= args.max_records:
                    logger.info(f"Reached maximum records limit: {args.max_records}")
                    break
            
            # Combine all batches
            if all_data:
                case_data = pd.concat(all_data, ignore_index=True)
            else:
                logger.error("No data extracted")
                return 1
                
        else:
            # Extract all data at once
            case_data = sfdc_client.get_case_data(start_date, end_date)
            
            if args.max_records and len(case_data) > args.max_records:
                case_data = case_data.head(args.max_records)
                logger.info(f"Limited data to {args.max_records} records")
        
        logger.info(f"Extracted {len(case_data)} case records")
        
        # Process text data
        logger.info("Processing text data...")
        processed_data = text_processor.preprocess_case_data(case_data)
        
        # Get text statistics
        stats = text_processor.get_text_stats(processed_data)
        logger.info(f"Text processing complete. Stats: {stats}")
        
        # Build vector index
        logger.info("Building FAISS vector index...")
        vector_db.build_index(processed_data)
        
        # Save index
        logger.info("Saving vector index...")
        if args.output_dir:
            # Create custom paths
            output_path = Path(args.output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            
            index_path = output_path / "faiss_index.bin"
            metadata_path = output_path / "case_metadata.json"
            
            vector_db.save_index(str(index_path), str(metadata_path))
        else:
            # Use default paths
            vector_db.save_index()
        
        # Get final statistics
        db_stats = vector_db.get_stats()
        logger.info(f"Index build complete! Final stats: {db_stats}")
        
        # Test search functionality
        logger.info("Testing search functionality...")
        test_results = vector_db.search("unexpected reboots", top_k=5)
        logger.info(f"Test search returned {len(test_results)} results")
        
        logger.info("FAISS index build process completed successfully!")
        return 0
        
    except Exception as e:
        logger.error(f"Error during index build: {e}")
        return 1


if __name__ == "__main__":
    import pandas as pd
    sys.exit(main())