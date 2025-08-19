"""Salesforce data extraction client for KMS-SFDC Vector Database."""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Iterator
import pandas as pd
from simple_salesforce import Salesforce
from loguru import logger
import base64

from ..utils.config import config
from ..utils.text_extractor import extract_text_from_attachments


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
            "TextBody": "TextBody__c",
            "Description_Summary": "Description_Summary__c",
            "Comment_Body_Text": "Comment_Body_Text__c"
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
    
    def get_case_attachments(self, case_ids: List[str]) -> Dict[str, List[Dict]]:
        """
        Fetch attachments for given case IDs.
        
        Args:
            case_ids: List of case IDs to fetch attachments for
            
        Returns:
            Dictionary mapping case ID to list of attachment data
        """
        if not case_ids:
            return {}
        
        logger.info(f"Fetching attachments for {len(case_ids)} cases")
        
        # Query attachments for the given case IDs
        case_ids_str = "', '".join(case_ids)
        query = f"""
        SELECT Id, ParentId, Name, Body, ContentType, BodyLength
        FROM Attachment 
        WHERE ParentId IN ('{case_ids_str}')
        AND ContentType IN ('application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'text/plain')
        """
        
        try:
            result = self.sf.query_all(query)
            attachments = result['records']
            
            # Group attachments by case ID
            case_attachments = {}
            for attachment in attachments:
                case_id = attachment['ParentId']
                if case_id not in case_attachments:
                    case_attachments[case_id] = []
                
                # Decode base64 body
                if attachment.get('Body'):
                    try:
                        attachment['Body'] = base64.b64decode(attachment['Body'])
                    except Exception as e:
                        logger.warning(f"Failed to decode attachment {attachment['Name']}: {e}")
                        continue
                
                case_attachments[case_id].append(attachment)
            
            logger.info(f"Retrieved {len(attachments)} attachments for {len(case_attachments)} cases")
            return case_attachments
            
        except Exception as e:
            logger.error(f"Error fetching attachments: {e}")
            return {}
    
    def get_case_content_documents(self, case_ids: List[str]) -> Dict[str, List[Dict]]:
        """
        Fetch ContentDocument files for given case IDs.
        
        Args:
            case_ids: List of case IDs to fetch files for
            
        Returns:
            Dictionary mapping case ID to list of file data
        """
        if not case_ids:
            return {}
        
        logger.info(f"Fetching ContentDocument files for {len(case_ids)} cases")
        
        # First get ContentDocumentIds linked to these cases
        case_ids_str = "', '".join(case_ids)
        link_query = f"""
        SELECT ContentDocumentId, LinkedEntityId
        FROM ContentDocumentLink 
        WHERE LinkedEntityId IN ('{case_ids_str}')
        """
        
        try:
            result = self.sf.query_all(link_query)
            links = result['records']
            
            if not links:
                logger.info("No ContentDocument links found")
                return {}
            
            # Get ContentDocumentIds
            content_doc_ids = list(set([link['ContentDocumentId'] for link in links]))
            content_doc_ids_str = "', '".join(content_doc_ids)
            
            # Get the actual ContentDocument data
            content_query = f"""
            SELECT Id, Title, FileType, ContentSize, LatestPublishedVersionId
            FROM ContentDocument 
            WHERE Id IN ('{content_doc_ids_str}')
            """
            
            result = self.sf.query_all(content_query)
            content_docs = result['records']
            
            # Get ContentVersion data (the actual file content)
            version_ids = [doc['LatestPublishedVersionId'] for doc in content_docs if doc.get('LatestPublishedVersionId')]
            if not version_ids:
                logger.info("No ContentVersion IDs found")
                return {}
            
            version_ids_str = "', '".join(version_ids)
            version_query = f"""
            SELECT Id, ContentDocumentId, Title, FileType, ContentSize, PathOnClient
            FROM ContentVersion 
            WHERE Id IN ('{version_ids_str}')
            """
            
            result = self.sf.query_all(version_query)
            versions = result['records']
            
            # Group files by case ID and download content using REST API
            case_files = {}
            for link in links:
                case_id = link['LinkedEntityId']
                content_doc_id = link['ContentDocumentId']
                
                # Find the content document
                content_doc = next((doc for doc in content_docs if doc['Id'] == content_doc_id), None)
                if not content_doc:
                    continue
                
                # Find the version
                version = next((v for v in versions if v['ContentDocumentId'] == content_doc_id), None)
                if not version:
                    continue
                
                # Download file content using REST API
                try:
                    # Use the REST API to download the file content
                    version_id = version['Id']
                    url = f"{self.sf.base_url}sobjects/ContentVersion/{version_id}/VersionData"
                    
                    headers = {
                        'Authorization': f'Bearer {self.sf.session_id}',
                        'Content-Type': 'application/json'
                    }
                    
                    import requests
                    response = requests.get(url, headers=headers)
                    
                    if response.status_code == 200:
                        file_content = response.content
                        
                        if case_id not in case_files:
                            case_files[case_id] = []
                        
                        case_files[case_id].append({
                            'Name': version['Title'],
                            'Body': file_content,
                            'ContentType': version['FileType'],
                            'ContentSize': version['ContentSize']
                        })
                        
                        logger.info(f"Successfully downloaded {version['Title']} ({len(file_content)} bytes)")
                    else:
                        logger.warning(f"Failed to download {version['Title']}: HTTP {response.status_code}")
                        
                except Exception as e:
                    logger.warning(f"Failed to download file {version['Title']}: {e}")
                    continue
            
            logger.info(f"Retrieved {len(versions)} ContentDocument files for {len(case_files)} cases")
            return case_files
            
        except Exception as e:
            logger.error(f"Error fetching ContentDocument files: {e}")
            return {}
    
    def get_case_data_with_attachments(self, start_date: Optional[datetime] = None, 
                                      end_date: Optional[datetime] = None) -> pd.DataFrame:
        """
        Extract case data and add attachment content to Description field.
        
        Args:
            start_date: Start date for data extraction (defaults to 2 years ago)
            end_date: End date for data extraction (defaults to now)
            
        Returns:
            DataFrame containing case data with attachment content added to Description
        """
        # First get the case data
        df = self.get_case_data(start_date, end_date)
        
        if df.empty:
            return df
        
        # Get case IDs
        case_ids = df['Id'].tolist()
        
        # Fetch attachments
        case_attachments = self.get_case_attachments(case_ids)
        
        # Add attachment text to Description field
        for i, case_id in enumerate(case_ids):
            attachments = case_attachments.get(case_id, [])
            if attachments:
                attachment_text = extract_text_from_attachments(attachments)
                if attachment_text:
                    # Add attachment text to existing Description field
                    current_desc = df.at[i, 'Description_Description__c'] if 'Description_Description__c' in df.columns else ""
                    if current_desc:
                        df.at[i, 'Description_Description__c'] = current_desc + "\n\nAttachment Content:\n" + attachment_text
                    else:
                        df.at[i, 'Description_Description__c'] = "Attachment Content:\n" + attachment_text
        
        # Log summary
        cases_with_attachments = sum(1 for case_id in case_ids if case_attachments.get(case_id))
        logger.info(f"Added attachment content to {cases_with_attachments} out of {len(df)} cases")
        
        return df
    
    def get_case_data_with_content_documents(self, start_date: Optional[datetime] = None, 
                                           end_date: Optional[datetime] = None) -> pd.DataFrame:
        """
        Extract case data and add ContentDocument file content to Description field.
        
        Args:
            start_date: Start date for data extraction (defaults to 2 years ago)
            end_date: End date for data extraction (defaults to now)
            
        Returns:
            DataFrame containing case data with file content added to Description
        """
        # First get the case data
        df = self.get_case_data(start_date, end_date)
        
        if df.empty:
            return df
        
        # Get case IDs
        case_ids = df['Id'].tolist()
        
        # Fetch ContentDocument files
        case_files = self.get_case_content_documents(case_ids)
        
        # Add file text to Description field
        for i, case_id in enumerate(case_ids):
            files = case_files.get(case_id, [])
            if files:
                file_text = extract_text_from_attachments(files)
                if file_text:
                    # Add file text to existing Description field
                    current_desc = df.at[i, 'Description_Description__c'] if 'Description_Description__c' in df.columns else ""
                    if current_desc:
                        df.at[i, 'Description_Description__c'] = current_desc + "\n\nFile Content:\n" + file_text
                    else:
                        df.at[i, 'Description_Description__c'] = "File Content:\n" + file_text
        
        # Log summary
        cases_with_files = sum(1 for case_id in case_ids if case_files.get(case_id))
        logger.info(f"Added file content to {cases_with_files} out of {len(df)} cases")
        
        return df
    
    # Alias for backward compatibility
    def extract_case_data_batched(self, start_date: Optional[datetime] = None,
                                 end_date: Optional[datetime] = None,
                                 batch_size: int = 2000) -> Iterator[pd.DataFrame]:
        """Alias for get_case_data_batch for backward compatibility."""
        return self.get_case_data_batch(start_date, end_date)