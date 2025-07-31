#!/usr/bin/env python3
"""Check available fields in Salesforce Case object."""

import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent))

from src.data_extraction.sfdc_client import SFDCClient
from loguru import logger
import json

def main():
    """Check available Case fields in Salesforce."""
    try:
        logger.info("Connecting to Salesforce to check Case fields...")
        
        # Initialize SFDC client
        sfdc_client = SFDCClient()
        
        # Get Case field information
        logger.info("Retrieving Case object field metadata...")
        fields_info = sfdc_client.get_case_fields_info()
        
        # Filter and display relevant text fields
        text_fields = []
        for field_name, field_info in fields_info.items():
            if field_info['type'] in ['string', 'textarea', 'picklist']:
                text_fields.append({
                    'name': field_name,
                    'label': field_info['label'],
                    'type': field_info['type'],
                    'custom': field_info['custom']
                })
        
        # Sort by name
        text_fields.sort(key=lambda x: x['name'])
        
        print("\n=== Available Text Fields in Case Object ===")
        print(f"{'Field Name':<30} {'Label':<40} {'Type':<15} {'Custom'}")
        print("-" * 95)
        
        for field in text_fields:
            print(f"{field['name']:<30} {field['label']:<40} {field['type']:<15} {field['custom']}")
        
        # Show suggested fields for vectorization
        suggested_fields = []
        for field in text_fields:
            name_lower = field['name'].lower()
            if any(keyword in name_lower for keyword in ['subject', 'description', 'comment', 'resolution', 'issue', 'cause', 'text', 'body']):
                suggested_fields.append(field['name'])
        
        print(f"\n=== Suggested Fields for Vectorization ===")
        for field in suggested_fields:
            print(f"  - \"{field}\"")
        
        # Create a simple test query
        print(f"\n=== Testing Sample Query ===")
        query_fields = ['Id', 'Subject', 'Description', 'Status']
        available_query_fields = [f for f in query_fields if f in fields_info]
        
        if available_query_fields:
            test_query = f"SELECT {', '.join(available_query_fields)} FROM Case LIMIT 1"
            print(f"Test query: {test_query}")
            
            try:
                result = sfdc_client.sf.query(test_query)
                print(f"Query successful! Found {result['totalSize']} records.")
                if result['records']:
                    print("Sample record:")
                    record = result['records'][0]
                    for field in available_query_fields:
                        value = record.get(field, 'N/A')
                        if isinstance(value, str) and len(value) > 50:
                            value = value[:50] + "..."
                        print(f"  {field}: {value}")
            except Exception as e:
                print(f"Test query failed: {e}")
        
        logger.info("Field analysis complete!")
        return 0
        
    except Exception as e:
        logger.error(f"Error checking SFDC fields: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())