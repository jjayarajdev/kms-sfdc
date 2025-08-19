#!/usr/bin/env python3
"""
Check Salesforce fields utility.
This script checks what fields are available in Salesforce objects.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from data_extraction.sfdc_client import SFDCClient
from utils.config import Config

def check_sfdc_fields():
    """Check available fields in Salesforce objects."""
    try:
        # Initialize configuration and client
        config = Config()
        sfdc_client = SFDCClient(config)
        
        print("Checking Salesforce fields...")
        
        # Check Case object fields
        print("\n1. Case object fields:")
        try:
            case_fields = sfdc_client.sf.Case.describe()
            field_names = [field['name'] for field in case_fields['fields']]
            print(f"Found {len(field_names)} fields in Case object")
            
            # Show all fields
            for field in field_names:
                print(f"  - {field}")
                
        except Exception as e:
            print(f"Error describing Case object: {e}")
        
        # Check Attachment object fields
        print("\n2. Attachment object fields:")
        try:
            attachment_fields = sfdc_client.sf.Attachment.describe()
            att_field_names = [field['name'] for field in attachment_fields['fields']]
            print(f"Found {len(att_field_names)} fields in Attachment object")
            
            # Show all fields
            for field in att_field_names:
                print(f"  - {field}")
                
        except Exception as e:
            print(f"Error describing Attachment object: {e}")
        
        # Check ContentDocument object fields
        print("\n3. ContentDocument object fields:")
        try:
            content_doc_fields = sfdc_client.sf.ContentDocument.describe()
            cd_field_names = [field['name'] for field in content_doc_fields['fields']]
            print(f"Found {len(cd_field_names)} fields in ContentDocument object")
            
            # Show all fields
            for field in cd_field_names:
                print(f"  - {field}")
                
        except Exception as e:
            print(f"Error describing ContentDocument object: {e}")
        
        # Check ContentVersion object fields
        print("\n4. ContentVersion object fields:")
        try:
            content_ver_fields = sfdc_client.sf.ContentVersion.describe()
            cv_field_names = [field['name'] for field in content_ver_fields['fields']]
            print(f"Found {len(cv_field_names)} fields in ContentVersion object")
            
            # Show all fields
            for field in cv_field_names:
                print(f"  - {field}")
                
        except Exception as e:
            print(f"Error describing ContentVersion object: {e}")
        
        print("\nField check complete!")
        
    except Exception as e:
        print(f"Error during field check: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_sfdc_fields()

