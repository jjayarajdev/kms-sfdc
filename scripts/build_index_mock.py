#!/usr/bin/env python3
"""Build FAISS index using mock SFDC data for testing."""

import sys
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
from loguru import logger

# Add src to path
sys.path.append(str(Path(__file__).parent.parent))

from src.utils import TextProcessor
from src.vectorization import VectorDatabase


def generate_mock_case_data(num_cases=1000):
    """Generate mock SFDC case data for testing."""
    logger.info(f"Generating {num_cases} mock SFDC cases...")
    
    # Sample subjects and descriptions
    subjects = [
        "Login authentication failure",
        "Password reset not working", 
        "System performance issues",
        "Database connection timeout",
        "API rate limit exceeded",
        "User permissions error",
        "Data sync failure",
        "Report generation slow",
        "Email notifications not sending",
        "Integration error with third-party"
    ]
    
    descriptions = [
        "User reports being unable to access the system despite using correct credentials.",
        "Customer cannot reset password through the standard reset flow.",
        "System is responding slowly during peak hours affecting productivity.",
        "Database queries are timing out causing application errors.",
        "API calls are being rejected due to rate limiting.",
        "User lacks necessary permissions to perform required actions.",
        "Data synchronization between systems has stopped working.",
        "Reports are taking excessive time to generate for users.",
        "Email notifications configured but not being delivered.",
        "Integration with external service is failing with authentication errors."
    ]
    
    resolutions = [
        "Reset user credentials and cleared browser cache. Issue resolved.",
        "Updated password reset token expiration settings. User able to reset.",
        "Optimized database queries and added caching. Performance improved.",
        "Increased connection pool size and timeout values. Resolved timeouts.",
        "Implemented request throttling and retry logic. API calls successful.",
        "Updated user role permissions in admin console. Access granted.",
        "Restarted sync service and cleared queue. Synchronization resumed.",
        "Added database indexes for report queries. Generation time reduced.",
        "Updated SMTP configuration and verified settings. Emails delivering.",
        "Renewed API credentials and updated integration. Connection restored."
    ]
    
    # Generate random cases
    cases = []
    for i in range(num_cases):
        case = {
            'Id': f'500XX{str(i).zfill(7)}',
            'CaseNumber': f'{str(10000 + i).zfill(8)}',
            'Subject': np.random.choice(subjects),
            'Description': np.random.choice(descriptions),
            'Resolution__c': np.random.choice(resolutions),
            'Case_Notes__c': f"Additional notes for case {i}. Follow-up may be required.",
            'Status': np.random.choice(['Open', 'Closed', 'In Progress', 'Escalated']),
            'Priority': np.random.choice(['Low', 'Medium', 'High', 'Critical']),
            'Origin': np.random.choice(['Web', 'Email', 'Phone', 'Chat']),
            'Type': np.random.choice(['Problem', 'Question', 'Feature Request', 'Bug']),
            'Reason': np.random.choice(['Technical Issue', 'User Error', 'Configuration', 'Other']),
            'CreatedDate': datetime.now() - timedelta(days=np.random.randint(1, 730)),
            'LastModifiedDate': datetime.now() - timedelta(days=np.random.randint(0, 30))
        }
        cases.append(case)
    
    df = pd.DataFrame(cases)
    logger.info(f"Generated {len(df)} mock cases")
    return df


def main():
    """Main function to build vector index from mock data."""
    # Configure logging
    logger.add(
        "logs/build_index_mock_{time}.log",
        rotation="10 MB",
        retention="10 days",
        level="INFO"
    )
    
    logger.info("Starting FAISS index build with mock data")
    
    try:
        # Generate mock data
        num_cases = 1000  # Adjust as needed
        case_data = generate_mock_case_data(num_cases)
        
        # Initialize text processor
        logger.info("Initializing text processor...")
        text_processor = TextProcessor()
        
        # Process text data
        logger.info("Processing text data...")
        processed_data = text_processor.preprocess_case_data(case_data)
        
        # Get text statistics
        stats = text_processor.get_text_stats(processed_data)
        logger.info(f"Text processing complete. Stats: {stats}")
        
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
        test_queries = [
            "login authentication issues",
            "password reset problems",
            "system performance slow"
        ]
        
        for query in test_queries:
            results = vector_db.search(query, top_k=3)
            logger.info(f"Query '{query}' returned {len(results)} results")
            if results:
                logger.info(f"  Top result: {results[0]['subject']} (score: {results[0]['similarity_score']:.3f})")
        
        logger.info("Mock data index build completed successfully!")
        logger.info(f"\nYou can now test the API with: make run-api")
        return 0
        
    except Exception as e:
        logger.error(f"Error during mock index build: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())