#!/usr/bin/env python3
"""
Cognate AI Integration Script for KMS-SFDC Vector Database.

This script demonstrates how the FAISS vector database integrates with
Cognate AI to replace Coveo API2 lexical search with semantic vector search.
"""

import sys
import json
from pathlib import Path
from typing import Dict, List, Optional
from loguru import logger

# Add src to path
sys.path.append(str(Path(__file__).parent.parent))

from src.vectorization import VectorDatabase
from src.utils.config import config


class CognateAIIntegration:
    """Integration layer between FAISS Vector DB and Cognate AI."""
    
    def __init__(self):
        """Initialize Cognate AI integration."""
        self.vector_db = VectorDatabase()
        self.is_ready = False
        
    def initialize(self) -> bool:
        """
        Initialize the integration by loading the vector database.
        
        Returns:
            True if initialization successful
        """
        try:
            logger.info("Initializing Cognate AI integration...")
            
            # Load existing vector database
            self.vector_db.load_index()
            self.is_ready = True
            
            logger.info("Cognate AI integration initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Cognate AI integration: {e}")
            return False
    
    def search_similar_cases(self, query: str, max_results: int = 10, 
                           min_similarity: float = 0.7) -> Dict:
        """
        Search for similar cases to replace Coveo API2 functionality.
        
        This method provides the same interface that Cognate AI expects
        from the previous Coveo API2 integration.
        
        Args:
            query: Search query text
            max_results: Maximum number of results to return
            min_similarity: Minimum similarity threshold
            
        Returns:
            Search results in Cognate AI compatible format
        """
        if not self.is_ready:
            return {
                'status': 'error',
                'message': 'Vector database not initialized',
                'results': []
            }
        
        try:
            # Perform vector similarity search
            results = self.vector_db.search(
                query_text=query,
                top_k=max_results,
                similarity_threshold=min_similarity
            )
            
            # Transform results to Cognate AI expected format
            formatted_results = []
            for result in results:
                formatted_result = {
                    'id': result['case_id'],
                    'case_number': result['case_number'],
                    'title': result['subject'],
                    'snippet': result['preview_text'],
                    'relevance_score': result['similarity_score'],
                    'metadata': {
                        'status': result['status'],
                        'priority': result['priority'],
                        'created_date': result['created_date'],
                        'source': 'FAISS_VECTOR_DB'
                    }
                }
                formatted_results.append(formatted_result)
            
            response = {
                'status': 'success',
                'query': query,
                'total_results': len(formatted_results),
                'results': formatted_results,
                'search_metadata': {
                    'search_type': 'semantic_vector',
                    'model': config.vectordb.model_name,
                    'min_similarity': min_similarity,
                    'replaced_service': 'Coveo_API2'
                }
            }
            
            logger.info(f"Cognate AI search completed: {len(formatted_results)} results")
            return response
            
        except Exception as e:
            logger.error(f"Error in Cognate AI search: {e}")
            return {
                'status': 'error',
                'message': str(e),
                'results': []
            }
    
    def get_case_details(self, case_id: str) -> Optional[Dict]:
        """
        Get detailed information for a specific case.
        
        Args:
            case_id: Case ID to retrieve
            
        Returns:
            Case details or None if not found
        """
        try:
            # In a full implementation, this would query the vector DB metadata
            # For now, this is a placeholder showing the expected interface
            
            logger.info(f"Retrieving case details for: {case_id}")
            
            # Placeholder implementation
            case_details = {
                'case_id': case_id,
                'case_number': f'00{case_id[-6:]}',
                'subject': 'Case subject retrieved from vector DB',
                'description': 'Full case description...',
                'resolution': 'Case resolution details...',
                'status': 'Closed',
                'priority': 'Medium',
                'created_date': '2023-01-15T10:30:00Z',
                'last_modified': '2023-01-20T14:45:00Z'
            }
            
            return case_details
            
        except Exception as e:
            logger.error(f"Error retrieving case details: {e}")
            return None
    
    def health_check(self) -> Dict:
        """
        Health check for Cognate AI integration.
        
        Returns:
            Health status information
        """
        try:
            vector_stats = self.vector_db.get_stats()
            
            health_status = {
                'status': 'healthy' if self.is_ready else 'unhealthy',
                'vector_db_ready': vector_stats['is_trained'],
                'total_vectors': vector_stats['total_vectors'],
                'model_name': vector_stats['model_name'],
                'integration_ready': self.is_ready,
                'replacement_target': 'Coveo_API2',
                'search_capability': 'semantic_vector_search'
            }
            
            return health_status
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                'status': 'unhealthy',
                'error': str(e)
            }
    
    def performance_metrics(self) -> Dict:
        """
        Get performance metrics for monitoring.
        
        Returns:
            Performance metrics
        """
        try:
            stats = self.vector_db.get_stats()
            
            metrics = {
                'total_indexed_cases': stats['total_vectors'],
                'index_size_mb': 0,  # Would calculate actual size
                'average_query_time_ms': 0,  # Would track query performance
                'success_rate': 1.0,  # Would track search success rate
                'cache_hit_rate': 0.0,  # If caching is implemented
                'model_info': {
                    'name': stats['model_name'],
                    'dimension': stats['dimension'],
                    'type': stats['index_type']
                }
            }
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error getting performance metrics: {e}")
            return {}


def demonstrate_cognate_ai_integration():
    """Demonstrate the Cognate AI integration functionality."""
    logger.info("=== Cognate AI Integration Demonstration ===")
    
    # Initialize integration
    integration = CognateAIIntegration()
    
    if not integration.initialize():
        logger.error("Failed to initialize integration")
        return False
    
    # Test health check
    logger.info("Testing health check...")
    health = integration.health_check()
    logger.info(f"Health status: {json.dumps(health, indent=2)}")
    
    # Test search functionality (replacing Coveo API2)
    logger.info("Testing semantic search (replacing Coveo API2)...")
    test_queries = [
        "user login issues",
        "password reset problems", 
        "system performance slow"
    ]
    
    for query in test_queries:
        logger.info(f"Searching for: '{query}'")
        results = integration.search_similar_cases(query, max_results=5)
        logger.info(f"Found {results.get('total_results', 0)} results")
        
        if results['status'] == 'success' and results['results']:
            logger.info("Top result:")
            top_result = results['results'][0]
            logger.info(f"  Case: {top_result['case_number']}")
            logger.info(f"  Title: {top_result['title']}")
            logger.info(f"  Relevance: {top_result['relevance_score']:.3f}")
    
    # Test performance metrics
    logger.info("Getting performance metrics...")
    metrics = integration.performance_metrics()
    logger.info(f"Performance metrics: {json.dumps(metrics, indent=2)}")
    
    logger.info("=== Integration demonstration completed ===")
    return True


def main():
    """Main function for Cognate AI integration testing."""
    logger.add(
        "logs/cognate_ai_integration_{time}.log",
        rotation="10 MB", 
        retention="10 days",
        level="INFO"
    )
    
    success = demonstrate_cognate_ai_integration()
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())