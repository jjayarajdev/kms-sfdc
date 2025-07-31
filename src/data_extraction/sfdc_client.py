"""Salesforce data extraction client for KMS-SFDC Vector Database."""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Iterator
import pandas as pd
from simple_salesforce import Salesforce
from loguru import logger

from ..utils.config import config


class SFDCClient:
    """Client for extracting case data from Salesforce."""
    
    def __init__(self):
        """Initialize Salesforce connection."""
        self.sf_config = config.salesforce
        self.sf = None
        self._connect()
    
    def _connect(self) -> None:
        """Establish connection to Salesforce."""
        try:
            # Extract domain from login_url for simple-salesforce
            login_url = self.sf_config.login_url.rstrip('/')
            if 'login.salesforce.com' in login_url:
                domain = 'login'
            elif 'test.salesforce.com' in login_url:
                domain = 'test'
            else:
                # Extract domain from custom URLs like https://mydomain.my.salesforce.com/
                domain = login_url.replace('https://', '').replace('http://', '').split('.')[0]
            
            logger.info(f"Connecting to Salesforce with:")
            logger.info(f"  Username: {self.sf_config.username}")
            logger.info(f"  Login URL: {login_url}")
            logger.info(f"  Domain: {domain}")
            logger.info(f"  API Version: {self.sf_config.api_version}")
            logger.info(f"  Security Token: {'*' * len(self.sf_config.security_token)}")
            
            # simple-salesforce uses username/password/token authentication
            self.sf = Salesforce(
                username=self.sf_config.username,
                password=self.sf_config.password,
                security_token=self.sf_config.security_token,
                domain=domain,
                version=self.sf_config.api_version
            )
            logger.info("Successfully connected to Salesforce")
        except Exception as e:
            logger.error(f"Failed to connect to Salesforce: {e}")
            raise
    
    def get_case_data(self, start_date: Optional[datetime] = None, 
                     end_date: Optional[datetime] = None) -> pd.DataFrame:
        """
        Extract case data from Salesforce within the specified date range.
        
        Args:
            start_date: Start date for data extraction (defaults to 2 years ago)
            end_date: End date for data extraction (defaults to now)
            
        Returns:
            DataFrame containing case data
        """
        if start_date is None:
            start_date = datetime.now() - timedelta(days=365 * self.sf_config.date_range_years)
        if end_date is None:
            end_date = datetime.now()
        
        logger.info(f"Extracting case data from {start_date} to {end_date}")
        
        # Build SOQL query for case data
        query = self._build_case_query(start_date, end_date)
        
        # Execute query and collect results
        all_records = []
        try:
            result = self.sf.query_all(query)
            all_records = result['records']
            
            logger.info(f"Retrieved {len(all_records)} case records")
            
            # Convert to DataFrame
            df = pd.DataFrame(all_records)
            
            # Clean up Salesforce metadata columns
            if 'attributes' in df.columns:
                df = df.drop(columns=['attributes'])
            
            return df
            
        except Exception as e:
            logger.error(f"Error extracting case data: {e}")
            raise
    
    def get_case_data_batch(self, start_date: Optional[datetime] = None,
                           end_date: Optional[datetime] = None) -> Iterator[pd.DataFrame]:
        """
        Extract case data in batches for memory efficiency.
        
        Args:
            start_date: Start date for data extraction
            end_date: End date for data extraction
            
        Yields:
            DataFrame batches containing case data
        """
        if start_date is None:
            start_date = datetime.now() - timedelta(days=365 * self.sf_config.date_range_years)
        if end_date is None:
            end_date = datetime.now()
        
        query = self._build_case_query(start_date, end_date)
        
        try:
            # Use query instead of query_all for batched results
            result = self.sf.query(query)
            
            while True:
                records = result['records']
                if records:
                    df = pd.DataFrame(records)
                    if 'attributes' in df.columns:
                        df = df.drop(columns=['attributes'])
                    yield df
                
                # Check if there are more records
                if result['done']:
                    break
                else:
                    result = self.sf.query_more(result['nextRecordsUrl'], True)
                    
        except Exception as e:
            logger.error(f"Error in batch extraction: {e}")
            raise
    
    def _build_case_query(self, start_date: datetime, end_date: datetime) -> str:
        """
        Build SOQL query for case data extraction.
        
        Args:
            start_date: Start date for filtering
            end_date: End date for filtering
            
        Returns:
            SOQL query string
        """
        # Field mapping from config names to actual SFDC field names
        field_mapping = {
            "Case_Number": "Case_Number__c",
            "Subject_Description": "Subject_Description__c", 
            "Description_Description": "Description_Description__c",
            "Issue_Plain_Text": "Issue_Plain_Text__c",
            "Cause_Plain_Text": "Cause_Plain_Text__c", 
            "Resolution_Plain_Text": "Resolution_Plain_Text__c",
            "Status_Text": "Status_Text__c",
            "TextBody": "TextBody__c"
        }
        
        # Get fields to extract from config and map them
        config_text_fields = config.text_processing.fields_to_vectorize
        text_fields = [field_mapping.get(field, field) for field in config_text_fields]
        
        # Standard case fields we always need
        standard_fields = [
            'Id', 'CaseNumber', 'CreatedDate', 'LastModifiedDate',
            'Status', 'Priority', 'Origin', 'Type', 'Reason'
        ]
        
        # Combine all fields and remove duplicates
        all_fields = list(set(standard_fields + text_fields))
        fields_str = ', '.join(all_fields)
        
        # Format dates for SOQL
        start_str = start_date.strftime("%Y-%m-%dT%H:%M:%S.000+0000")
        end_str = end_date.strftime("%Y-%m-%dT%H:%M:%S.000+0000")
        
        query = f"""
        SELECT {fields_str}
        FROM Case 
        WHERE CreatedDate >= {start_str} 
          AND CreatedDate <= {end_str}
          AND Status != 'Deleted'
        ORDER BY CreatedDate DESC
        """
        
        # Add record limit if specified
        if self.sf_config.max_records:
            query += f" LIMIT {self.sf_config.max_records}"
        
        logger.debug(f"SOQL Query: {query}")
        return query
    
    def get_case_fields_info(self) -> Dict:
        """Get metadata about Case object fields."""
        try:
            case_metadata = self.sf.Case.describe()
            fields_info = {}
            
            for field in case_metadata['fields']:
                fields_info[field['name']] = {
                    'label': field['label'],
                    'type': field['type'],
                    'length': field.get('length', 0),
                    'custom': field['custom']
                }
            
            return fields_info
            
        except Exception as e:
            logger.error(f"Error getting case fields info: {e}")
            raise
    
    def test_connection(self) -> bool:
        """Test Salesforce connection."""
        try:
            # Simple query to test connection
            result = self.sf.query("SELECT Id FROM Case LIMIT 1")
            logger.info("Salesforce connection test successful")
            return True
        except Exception as e:
            logger.error(f"Salesforce connection test failed: {e}")
            return False
    
    # Alias for backward compatibility
    def extract_case_data_batched(self, start_date: Optional[datetime] = None,
                                 end_date: Optional[datetime] = None,
                                 batch_size: int = 2000) -> Iterator[pd.DataFrame]:
        """Alias for get_case_data_batch for backward compatibility."""
        return self.get_case_data_batch(start_date, end_date)