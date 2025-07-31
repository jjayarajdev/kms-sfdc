"""
Integration tests for SFDC data extraction.
"""

import pytest
import pandas as pd
from unittest.mock import Mock, patch
from datetime import datetime, timedelta

from src.data_extraction.sfdc_client import SFDCClient
from src.utils.text_processor import TextProcessor


@pytest.mark.integration
class TestSFDCIntegration:
    """Integration tests for SFDC data extraction workflow."""

    @patch('simple_salesforce.Salesforce')
    def test_sfdc_to_text_processing_workflow(self, mock_sf, mock_config):
        """Test complete workflow from SFDC extraction to text processing."""
        # Mock SFDC response
        mock_sf_instance = Mock()
        mock_response = Mock()
        mock_response.records = [
            {
                'Id': 'case_001',
                'Case_Number__c': 'CASE-001',
                'Subject_Description__c': 'Server crashes during <b>peak hours</b>',
                'Description_Description__c': 'Production server experiencing crashes. Contact support@company.com for details.',
                'Issue_Plain_Text__c': 'Critical server instability',
                'Cause_Plain_Text__c': 'Memory overflow during high load',
                'Resolution_Plain_Text__c': 'Increased memory allocation and monitoring',
                'Status_Text__c': 'Closed',
                'TextBody__c': 'Additional technical details about the server issue',
                'CreatedDate': '2024-01-01T10:00:00.000+0000'
            },
            {
                'Id': 'case_002',
                'Case_Number__c': 'CASE-002',
                'Subject_Description__c': 'Database connection timeout',
                'Description_Description__c': 'Users unable to connect to database after 30 seconds',
                'Issue_Plain_Text__c': 'Database connectivity problems',
                'Cause_Plain_Text__c': 'Connection pool exhaustion',
                'Resolution_Plain_Text__c': 'Optimized connection pool settings',
                'Status_Text__c': 'Resolved',
                'TextBody__c': 'Database performance optimization details',
                'CreatedDate': '2024-01-02T14:30:00.000+0000'
            }
        ]
        mock_response.done = True
        mock_sf_instance.query_all.return_value = mock_response
        mock_sf.return_value = mock_sf_instance
        
        with patch('src.data_extraction.sfdc_client.config', mock_config):
            with patch('src.utils.text_processor.config', mock_config):
                # Step 1: Extract data from SFDC
                sfdc_client = SFDCClient()
                raw_data = sfdc_client.extract_case_data()
                
                assert isinstance(raw_data, pd.DataFrame)
                assert len(raw_data) == 2
                assert 'Case_Number' in raw_data.columns
                assert 'Subject_Description' in raw_data.columns
                
                # Verify field mapping worked
                assert raw_data.iloc[0]['Case_Number'] == 'CASE-001'
                assert raw_data.iloc[0]['Subject_Description'] == 'Server crashes during <b>peak hours</b>'
                
                # Step 2: Process text data
                text_processor = TextProcessor()
                processed_data = text_processor.preprocess_case_data(raw_data)
                
                assert isinstance(processed_data, pd.DataFrame)
                assert 'combined_text' in processed_data.columns
                
                # Verify HTML was cleaned
                combined_text = processed_data.iloc[0]['combined_text']
                assert '<b>' not in combined_text
                assert 'peak hours' in combined_text.lower()
                
                # Verify email was removed
                combined_text_case2 = processed_data.iloc[1]['combined_text']
                assert 'support@company.com' not in combined_text_case2

    @patch('simple_salesforce.Salesforce')
    def test_sfdc_batch_processing_integration(self, mock_sf, mock_config):
        """Test SFDC batch processing with large dataset."""
        # Create multiple batches of mock data
        batch1_records = [
            {
                'Id': f'case_{i:03d}',
                'Case_Number__c': f'CASE-{i:03d}',
                'Subject_Description__c': f'Test case {i}',
                'Description_Description__c': f'Description for case {i}',
                'Issue_Plain_Text__c': f'Issue {i}',
                'Resolution_Plain_Text__c': f'Resolution {i}',
                'Status_Text__c': 'Open',
                'CreatedDate': '2024-01-01T10:00:00.000+0000'
            }
            for i in range(1, 201)  # 200 records in first batch
        ]
        
        batch2_records = [
            {
                'Id': f'case_{i:03d}',
                'Case_Number__c': f'CASE-{i:03d}',
                'Subject_Description__c': f'Test case {i}',
                'Description_Description__c': f'Description for case {i}',
                'Issue_Plain_Text__c': f'Issue {i}',
                'Resolution_Plain_Text__c': f'Resolution {i}',
                'Status_Text__c': 'Closed',
                'CreatedDate': '2024-01-01T10:00:00.000+0000'
            }
            for i in range(201, 251)  # 50 records in second batch
        ]
        
        # Mock batched responses
        mock_sf_instance = Mock()
        
        batch_responses = [
            Mock(records=batch1_records, done=False),
            Mock(records=batch2_records, done=True)
        ]
        
        mock_sf_instance.query_all.side_effect = batch_responses
        mock_sf.return_value = mock_sf_instance
        
        with patch('src.data_extraction.sfdc_client.config', mock_config):
            sfdc_client = SFDCClient()
            
            # Test batched extraction
            all_batches = []
            for batch_data in sfdc_client.extract_case_data_batched(batch_size=200):
                all_batches.append(batch_data)
            
            # Should have received 2 batches
            assert len(all_batches) == 2
            assert len(all_batches[0]) == 200
            assert len(all_batches[1]) == 50
            
            # Combine all data
            combined_data = pd.concat(all_batches, ignore_index=True)
            assert len(combined_data) == 250

    @patch('simple_salesforce.Salesforce')
    def test_sfdc_field_validation_integration(self, mock_sf, mock_config):
        """Test field validation with actual SFDC field info."""
        # Mock SFDC field description
        mock_sf_instance = Mock()
        mock_field_info = {
            'fields': [
                {'name': 'Id', 'type': 'id', 'label': 'Case ID'},
                {'name': 'Case_Number__c', 'type': 'string', 'label': 'Case Number'},
                {'name': 'Subject_Description__c', 'type': 'textarea', 'label': 'Subject'},
                {'name': 'Issue_Plain_Text__c', 'type': 'textarea', 'label': 'Issue'},
                {'name': 'Status_Text__c', 'type': 'picklist', 'label': 'Status'},
                # Missing some fields that are in config
            ]
        }
        mock_sf_instance.Case.describe.return_value = mock_field_info
        mock_sf.return_value = mock_sf_instance
        
        with patch('src.data_extraction.sfdc_client.config', mock_config):
            sfdc_client = SFDCClient()
            
            # Get available fields
            fields_info = sfdc_client.get_case_fields_info()
            available_fields = list(fields_info.keys())
            
            # Validate field mapping
            missing_fields = sfdc_client.validate_field_mapping(available_fields)
            
            # Should identify missing fields
            assert isinstance(missing_fields, list)
            # Should find some missing fields since we didn't include all in mock
            assert 'Resolution_Plain_Text__c' in missing_fields

    @patch('simple_salesforce.Salesforce')
    def test_sfdc_error_handling_integration(self, mock_sf, mock_config):
        """Test error handling in SFDC integration."""
        mock_sf_instance = Mock()
        
        # Test connection error
        mock_sf.side_effect = Exception("INVALID_LOGIN: Invalid username, password, or security token")
        
        with patch('src.data_extraction.sfdc_client.config', mock_config):
            sfdc_client = SFDCClient()
            
            # Connection should fail
            connection_result = sfdc_client.test_connection()
            assert connection_result is False
        
        # Reset mock for query error test
        mock_sf.reset_mock()
        mock_sf.side_effect = None
        mock_sf.return_value = mock_sf_instance
        
        # Test query error
        mock_sf_instance.query_all.side_effect = Exception("INVALID_FIELD: No such column 'NonExistent__c'")
        
        with patch('src.data_extraction.sfdc_client.config', mock_config):
            sfdc_client = SFDCClient()
            
            with pytest.raises(Exception, match="INVALID_FIELD"):
                sfdc_client.extract_case_data()

    @patch('simple_salesforce.Salesforce')
    def test_sfdc_date_range_integration(self, mock_sf, mock_config):
        """Test SFDC extraction with date ranges."""
        mock_sf_instance = Mock()
        
        # Mock data with different creation dates
        mock_response = Mock()
        mock_response.records = [
            {
                'Id': 'case_001',
                'Case_Number__c': 'CASE-001',
                'Subject_Description__c': 'Recent case',
                'CreatedDate': '2024-01-15T10:00:00.000+0000'
            },
            {
                'Id': 'case_002',
                'Case_Number__c': 'CASE-002',
                'Subject_Description__c': 'Older case',
                'CreatedDate': '2023-06-01T10:00:00.000+0000'
            }
        ]
        mock_response.done = True
        mock_sf_instance.query_all.return_value = mock_response
        mock_sf.return_value = mock_sf_instance
        
        with patch('src.data_extraction.sfdc_client.config', mock_config):
            sfdc_client = SFDCClient()
            
            # Extract with date range
            start_date = datetime(2024, 1, 1)
            end_date = datetime(2024, 12, 31)
            
            data = sfdc_client.extract_case_data(start_date=start_date, end_date=end_date)
            
            # Verify query was called with date constraints
            query_call = mock_sf_instance.query_all.call_args[0][0]
            assert "2024-01-01T00:00:00.000+0000" in query_call
            assert "2024-12-31T00:00:00.000+0000" in query_call
            
            assert len(data) == 2  # Both records returned (filtering happens in SOQL)

    @patch('simple_salesforce.Salesforce')
    def test_sfdc_data_quality_integration(self, mock_sf, mock_config):
        """Test data quality handling in SFDC integration."""
        mock_sf_instance = Mock()
        
        # Mock data with quality issues
        mock_response = Mock()
        mock_response.records = [
            {
                'Id': 'case_001',
                'Case_Number__c': 'CASE-001',
                'Subject_Description__c': 'Good quality case with sufficient content',
                'Description_Description__c': 'Detailed description of the issue with technical details',
                'Issue_Plain_Text__c': 'Well-documented issue description',
                'Resolution_Plain_Text__c': 'Comprehensive resolution steps',
                'Status_Text__c': 'Closed',
                'CreatedDate': '2024-01-01T10:00:00.000+0000'
            },
            {
                'Id': 'case_002',
                'Case_Number__c': 'CASE-002',
                'Subject_Description__c': '',  # Empty subject
                'Description_Description__c': None,  # Null description
                'Issue_Plain_Text__c': 'x',  # Too short
                'Resolution_Plain_Text__c': '',
                'Status_Text__c': 'Open',
                'CreatedDate': '2024-01-02T10:00:00.000+0000'
            },
            {
                'Id': 'case_003',
                'Case_Number__c': 'CASE-003',
                'Subject_Description__c': 'the the the same same same text text',  # Repetitive
                'Description_Description__c': 'test test test test test test test',
                'Issue_Plain_Text__c': 'issue issue issue issue issue',
                'Resolution_Plain_Text__c': 'fix fix fix fix fix',
                'Status_Text__c': 'Closed',
                'CreatedDate': '2024-01-03T10:00:00.000+0000'
            }
        ]
        mock_response.done = True
        mock_sf_instance.query_all.return_value = mock_response
        mock_sf.return_value = mock_sf_instance
        
        with patch('src.data_extraction.sfdc_client.config', mock_config):
            with patch('src.utils.text_processor.config', mock_config):
                # Extract and process data
                sfdc_client = SFDCClient()
                raw_data = sfdc_client.extract_case_data()
                
                text_processor = TextProcessor()
                processed_data = text_processor.preprocess_case_data(raw_data)
                
                # Should filter out poor quality records
                assert len(processed_data) < len(raw_data)
                
                # Should keep the good quality record
                good_case = processed_data[processed_data['Id'] == 'case_001']
                assert len(good_case) == 1
                
                # Should have combined text
                assert 'combined_text' in processed_data.columns
                assert len(processed_data.iloc[0]['combined_text']) > 0

    @patch('simple_salesforce.Salesforce')
    def test_sfdc_large_scale_simulation(self, mock_sf, mock_config):
        """Test SFDC integration simulating large-scale data extraction."""
        mock_sf_instance = Mock()
        
        # Simulate large dataset by creating multiple batches
        total_records = 1000
        batch_size = 200
        
        batches = []
        for batch_num in range(0, total_records, batch_size):
            batch_records = []
            for i in range(batch_num, min(batch_num + batch_size, total_records)):
                batch_records.append({
                    'Id': f'case_{i:05d}',
                    'Case_Number__c': f'CASE-{i:05d}',
                    'Subject_Description__c': f'Large scale test case {i}',
                    'Description_Description__c': f'Detailed description for case {i} in large scale test',
                    'Issue_Plain_Text__c': f'Issue description for case {i}',
                    'Resolution_Plain_Text__c': f'Resolution for case {i}',
                    'Status_Text__c': 'Closed' if i % 2 == 0 else 'Open',
                    'CreatedDate': '2024-01-01T10:00:00.000+0000'
                })
            
            batches.append(Mock(records=batch_records, done=(batch_num + batch_size >= total_records)))
        
        mock_sf_instance.query_all.side_effect = batches
        mock_sf.return_value = mock_sf_instance
        
        with patch('src.data_extraction.sfdc_client.config', mock_config):
            sfdc_client = SFDCClient()
            
            # Extract data in batches
            all_data = []
            batch_count = 0
            
            for batch_data in sfdc_client.extract_case_data_batched(batch_size=batch_size):
                all_data.append(batch_data)
                batch_count += 1
                
                # Verify batch size (except possibly last batch)
                expected_size = min(batch_size, total_records - (batch_count - 1) * batch_size)
                assert len(batch_data) == expected_size
            
            # Verify total data
            combined_data = pd.concat(all_data, ignore_index=True)
            assert len(combined_data) == total_records
            
            # Verify data structure
            assert 'Case_Number' in combined_data.columns
            assert 'Subject_Description' in combined_data.columns
            
            # Check some sample data
            assert combined_data.iloc[0]['Case_Number'] == 'CASE-00000'
            assert combined_data.iloc[-1]['Case_Number'] == 'CASE-00999'

    @patch('simple_salesforce.Salesforce')
    def test_sfdc_field_mapping_edge_cases(self, mock_sf, mock_config):
        """Test field mapping with edge cases and missing fields."""
        mock_sf_instance = Mock()
        
        # Mock data with some missing fields
        mock_response = Mock()
        mock_response.records = [
            {
                'Id': 'case_001',
                'Case_Number__c': 'CASE-001',
                'Subject_Description__c': 'Complete record',
                'Description_Description__c': 'Full description',
                'Issue_Plain_Text__c': 'Issue text',
                'Resolution_Plain_Text__c': 'Resolution text',
                'Status_Text__c': 'Closed'
                # Missing some optional fields
            },
            {
                'Id': 'case_002',
                'Case_Number__c': 'CASE-002',
                'Subject_Description__c': 'Partial record',
                # Missing Description_Description__c
                'Issue_Plain_Text__c': 'Issue only',
                # Missing Resolution_Plain_Text__c
                'Status_Text__c': 'Open'
            }
        ]
        mock_response.done = True
        mock_sf_instance.query_all.return_value = mock_response
        mock_sf.return_value = mock_sf_instance
        
        with patch('src.data_extraction.sfdc_client.config', mock_config):
            sfdc_client = SFDCClient()
            data = sfdc_client.extract_case_data()
            
            assert len(data) == 2
            
            # Complete record should have all fields
            complete_record = data[data['Id'] == 'case_001'].iloc[0]
            assert complete_record['Subject_Description'] == 'Complete record'
            assert complete_record['Description_Description'] == 'Full description'
            
            # Partial record should handle missing fields gracefully
            partial_record = data[data['Id'] == 'case_002'].iloc[0]
            assert partial_record['Subject_Description'] == 'Partial record'
            # Missing fields should be None or empty
            assert pd.isna(partial_record['Description_Description']) or partial_record['Description_Description'] == ''

    @patch('simple_salesforce.Salesforce')
    def test_sfdc_connection_retry_integration(self, mock_sf, mock_config):
        """Test connection retry logic in SFDC integration."""
        # First attempt fails, second succeeds
        connection_attempts = [
            Exception("SERVER_UNAVAILABLE: Temporary server error"),
            Mock()  # Successful connection
        ]
        
        mock_sf.side_effect = connection_attempts
        
        with patch('src.data_extraction.sfdc_client.config', mock_config):
            # This would test retry logic if implemented in SFDCClient
            # For now, it tests that we can handle the first failure
            
            try:
                sfdc_client = SFDCClient()
                # First attempt should fail
                sfdc_client._connect()
                assert False, "Should have raised exception"
            except Exception as e:
                assert "SERVER_UNAVAILABLE" in str(e)
            
            # Reset mock for successful connection
            mock_sf.reset_mock()
            mock_sf_instance = Mock()
            mock_sf.return_value = mock_sf_instance
            mock_sf.side_effect = None
            
            # Second attempt should succeed
            sfdc_client = SFDCClient()
            sfdc_client._connect()
            assert sfdc_client.sf_client == mock_sf_instance