#!/usr/bin/env python3
"""
Test script for Salesforce attachment extraction functionality.
This script tests the basic attachment extraction from traditional Salesforce Attachment objects.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from data_extraction.sfdc_client import SFDCClient
from utils.config import Config
import pandas as pd

def test_attachment_extraction():
    """Test attachment extraction functionality."""
    try:
        # Initialize configuration and client
        config = Config()
        sfdc_client = SFDCClient(config)
        
        print("Testing attachment extraction...")
        
        # Get case data with attachments
        case_data = sfdc_client.get_case_data_with_attachments(
            batch_size=10,
            max_cases=5
        )
        
        if case_data.empty:
            print("No case data retrieved.")
            return
        
        print(f"Retrieved {len(case_data)} cases")
        
        # Check if attachment content was extracted
        attachment_cases = case_data[
            case_data['Description_Description__c'].str.contains('Attachment Content:', na=False)
        ]
        
        print(f"Cases with attachments: {len(attachment_cases)}")
        
        if not attachment_cases.empty:
            print("\nSample attachment content:")
            for idx, row in attachment_cases.head(2).iterrows():
                print(f"Case {row['CaseNumber']}: {row['Description_Description__c'][:200]}...")
        else:
            print("No attachment content found. Check if cases have attachments in Salesforce.")
            
    except Exception as e:
        print(f"Error testing attachment extraction: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_attachment_extraction()

