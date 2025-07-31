"""
Unit tests for SFDC client functionality.
"""

import pytest
import pandas as pd
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

from src.data_extraction.sfdc_client import SFDCClient


@pytest.mark.unit
class TestSFDCClient:
    """Test cases for SFDCClient class."""

    def test_init(self, mock_config):
        """Test SFDCClient initialization."""
        with patch('src.data_extraction.sfdc_client.config', mock_config):
            client = SFDCClient()
            
            assert client.config == mock_config.salesforce
            assert client.sf_client is None
            assert client.field_mapping is not None
            assert isinstance(client.field_mapping, dict)

    def test_field_mapping_structure(self, mock_config):
        """Test field mapping contains required fields."""
        with patch('src.data_extraction.sfdc_client.config', mock_config):
            client = SFDCClient()
            
            expected_fields = [
                'Case_Number', 'Subject_Description', 'Description_Description',
                'Issue_Plain_Text', 'Cause_Plain_Text', 'Resolution_Plain_Text',
                'Status_Text', 'TextBody'
            ]
            
            for field in expected_fields:
                assert field in client.field_mapping
                assert client.field_mapping[field].endswith('__c')

    @patch('simple_salesforce.Salesforce')
    def test_connect_success(self, mock_sf, mock_config):
        """Test successful connection to Salesforce."""
        mock_sf_instance = Mock()
        mock_sf.return_value = mock_sf_instance
        
        with patch('src.data_extraction.sfdc_client.config', mock_config):
            client = SFDCClient()
            client._connect()
            
            assert client.sf_client == mock_sf_instance
            mock_sf.assert_called_once_with(
                username=mock_config.salesforce.username,
                password=mock_config.salesforce.password,
                security_token=mock_config.salesforce.security_token,
                domain=mock_config.salesforce.login_url.split('//')[1].split('.')[0]
            )

    @patch('simple_salesforce.Salesforce')
    def test_connect_failure(self, mock_sf, mock_config):
        """Test connection failure handling."""
        mock_sf.side_effect = Exception("Connection failed")
        
        with patch('src.data_extraction.sfdc_client.config', mock_config):
            client = SFDCClient()
            
            with pytest.raises(Exception, match="Connection failed"):
                client._connect()

    def test_build_case_query_basic(self, mock_config):
        """Test basic SOQL query building."""
        with patch('src.data_extraction.sfdc_client.config', mock_config):
            client = SFDCClient()
            query = client._build_case_query()
            
            assert query.startswith("SELECT")
            assert "FROM Case" in query
            assert "WHERE" in query
            assert "ORDER BY CreatedDate DESC" in query
            
            # Check that mapped fields are included
            for field in client.field_mapping.values():
                assert field in query

    def test_build_case_query_with_date_range(self, mock_config):
        """Test query building with date range."""
        with patch('src.data_extraction.sfdc_client.config', mock_config):
            client = SFDCClient()
            start_date = datetime(2024, 1, 1)
            end_date = datetime(2024, 12, 31)
            
            query = client._build_case_query(start_date, end_date)
            
            assert "CreatedDate >= 2024-01-01T00:00:00.000+0000" in query
            assert "CreatedDate <= 2024-12-31T00:00:00.000+0000" in query

    def test_build_case_query_with_max_records(self, mock_config):
        """Test query building with record limit."""
        with patch('src.data_extraction.sfdc_client.config', mock_config):
            client = SFDCClient()
            query = client._build_case_query(max_records=1000)
            
            assert "LIMIT 1000" in query

    @patch('simple_salesforce.Salesforce')
    def test_test_connection_success(self, mock_sf, mock_config):
        """Test successful connection test."""
        mock_sf_instance = Mock()
        mock_sf_instance.query.return_value = {'totalSize': 1, 'records': [{'Id': 'test'}]}
        mock_sf.return_value = mock_sf_instance
        
        with patch('src.data_extraction.sfdc_client.config', mock_config):
            client = SFDCClient()
            result = client.test_connection()
            
            assert result is True

    @patch('simple_salesforce.Salesforce')
    def test_test_connection_failure(self, mock_sf, mock_config):
        """Test connection test failure."""
        mock_sf.side_effect = Exception("Test failed")
        
        with patch('src.data_extraction.sfdc_client.config', mock_config):
            client = SFDCClient()
            result = client.test_connection()
            
            assert result is False

    def test_process_case_batch(self, mock_config, mock_sfdc_response):
        """Test processing a batch of case records."""
        with patch('src.data_extraction.sfdc_client.config', mock_config):
            client = SFDCClient()
            df = client._process_case_batch(mock_sfdc_response.records)
            
            assert isinstance(df, pd.DataFrame)
            assert len(df) == 1
            assert 'Id' in df.columns
            assert 'Case_Number' in df.columns
            assert 'Subject_Description' in df.columns

    def test_process_case_batch_field_mapping(self, mock_config):
        """Test field mapping in batch processing."""
        test_records = [{
            'Id': 'test_001',
            'Case_Number__c': 'TEST-001',
            'Subject_Description__c': 'Test subject',
            'Status_Text__c': 'Open'
        }]
        
        with patch('src.data_extraction.sfdc_client.config', mock_config):
            client = SFDCClient()
            df = client._process_case_batch(test_records)
            
            # Check that SFDC fields are mapped to config fields
            assert df.iloc[0]['Case_Number'] == 'TEST-001'
            assert df.iloc[0]['Subject_Description'] == 'Test subject'
            assert df.iloc[0]['Status_Text'] == 'Open'

    def test_process_case_batch_empty(self, mock_config):
        """Test processing empty batch."""
        with patch('src.data_extraction.sfdc_client.config', mock_config):
            client = SFDCClient()
            df = client._process_case_batch([])
            
            assert isinstance(df, pd.DataFrame)
            assert len(df) == 0

    @patch('simple_salesforce.Salesforce')
    def test_extract_case_data_success(self, mock_sf, mock_config, mock_sfdc_response):
        """Test successful case data extraction."""
        mock_sf_instance = Mock()
        mock_sf_instance.query_all.return_value = mock_sfdc_response
        mock_sf.return_value = mock_sf_instance
        
        with patch('src.data_extraction.sfdc_client.config', mock_config):
            client = SFDCClient()
            df = client.extract_case_data()
            
            assert isinstance(df, pd.DataFrame)
            assert len(df) == 1
            mock_sf_instance.query_all.assert_called_once()

    @patch('simple_salesforce.Salesforce')
    def test_extract_case_data_with_params(self, mock_sf, mock_config, mock_sfdc_response):
        """Test case data extraction with parameters."""
        mock_sf_instance = Mock()
        mock_sf_instance.query_all.return_value = mock_sfdc_response
        mock_sf.return_value = mock_sf_instance
        
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 12, 31)
        
        with patch('src.data_extraction.sfdc_client.config', mock_config):
            client = SFDCClient()
            df = client.extract_case_data(start_date=start_date, end_date=end_date, max_records=100)
            
            assert isinstance(df, pd.DataFrame)
            mock_sf_instance.query_all.assert_called_once()
            
            # Verify query contains date range and limit
            call_args = mock_sf_instance.query_all.call_args[0][0]
            assert "2024-01-01T00:00:00.000+0000" in call_args
            assert "2024-12-31T00:00:00.000+0000" in call_args
            assert "LIMIT 100" in call_args

    @patch('simple_salesforce.Salesforce')
    def test_extract_case_data_batched(self, mock_sf, mock_config):
        """Test batched case data extraction."""
        # Create mock responses for multiple batches
        batch1_records = [{'Id': f'case_00{i}', 'Case_Number__c': f'CASE-00{i}'} for i in range(200)]
        batch2_records = [{'Id': f'case_0{200+i}', 'Case_Number__c': f'CASE-0{200+i}'} for i in range(100)]
        
        mock_sf_instance = Mock()
        mock_sf_instance.query_all.side_effect = [
            type('MockResponse', (), {'records': batch1_records, 'done': False})(),
            type('MockResponse', (), {'records': batch2_records, 'done': True})()
        ]
        mock_sf.return_value = mock_sf_instance
        
        with patch('src.data_extraction.sfdc_client.config', mock_config):
            client = SFDCClient()
            
            all_data = []
            for batch_df in client.extract_case_data_batched(batch_size=200):
                all_data.append(batch_df)
            
            assert len(all_data) == 2  # Two batches
            assert len(all_data[0]) == 200  # First batch size
            assert len(all_data[1]) == 100  # Second batch size

    @patch('simple_salesforce.Salesforce')
    def test_get_case_fields_info(self, mock_sf, mock_config):
        """Test getting case field information."""
        mock_field_info = {
            'fields': [
                {'name': 'Id', 'type': 'id', 'label': 'Case ID'},
                {'name': 'Case_Number__c', 'type': 'string', 'label': 'Case Number'},
                {'name': 'Subject_Description__c', 'type': 'textarea', 'label': 'Subject'}
            ]
        }
        
        mock_sf_instance = Mock()
        mock_sf_instance.Case.describe.return_value = mock_field_info
        mock_sf.return_value = mock_sf_instance
        
        with patch('src.data_extraction.sfdc_client.config', mock_config):
            client = SFDCClient()
            fields_info = client.get_case_fields_info()
            
            assert isinstance(fields_info, dict)
            assert len(fields_info) == 3
            assert 'Id' in fields_info
            assert fields_info['Case_Number__c']['type'] == 'string'

    def test_validate_field_mapping(self, mock_config):
        """Test field mapping validation."""
        with patch('src.data_extraction.sfdc_client.config', mock_config):
            client = SFDCClient()
            
            # Test with valid fields
            available_fields = ['Case_Number__c', 'Subject_Description__c', 'Status_Text__c']
            missing_fields = client.validate_field_mapping(available_fields)
            
            # Should find some missing fields since we're only providing 3 out of many
            assert isinstance(missing_fields, list)

    def test_get_date_range_default(self, mock_config):
        """Test default date range calculation."""
        mock_config.salesforce.date_range_years = 2
        
        with patch('src.data_extraction.sfdc_client.config', mock_config):
            client = SFDCClient()
            start_date, end_date = client._get_date_range()
            
            # Should be approximately 2 years ago to now
            now = datetime.now()
            expected_start = now - timedelta(days=2*365)
            
            assert abs((start_date - expected_start).days) <= 1
            assert abs((end_date - now).days) <= 1

    def test_get_date_range_custom(self, mock_config):
        """Test custom date range."""
        start = datetime(2024, 1, 1)
        end = datetime(2024, 12, 31)
        
        with patch('src.data_extraction.sfdc_client.config', mock_config):
            client = SFDCClient()
            start_date, end_date = client._get_date_range(start, end)
            
            assert start_date == start
            assert end_date == end

    def test_format_datetime_for_soql(self, mock_config):
        """Test SOQL datetime formatting."""
        test_date = datetime(2024, 6, 15, 14, 30, 45)
        
        with patch('src.data_extraction.sfdc_client.config', mock_config):
            client = SFDCClient()
            formatted = client._format_datetime_for_soql(test_date)
            
            assert formatted == "2024-06-15T14:30:45.000+0000"

    @patch('simple_salesforce.Salesforce')
    def test_extract_case_data_error_handling(self, mock_sf, mock_config):
        """Test error handling during data extraction."""
        mock_sf_instance = Mock()
        mock_sf_instance.query_all.side_effect = Exception("SOQL Error")
        mock_sf.return_value = mock_sf_instance
        
        with patch('src.data_extraction.sfdc_client.config', mock_config):
            client = SFDCClient()
            
            with pytest.raises(Exception, match="SOQL Error"):
                client.extract_case_data()

    def test_process_case_batch_missing_fields(self, mock_config):
        """Test processing batch with missing fields."""
        test_records = [{
            'Id': 'test_001',
            'Case_Number__c': 'TEST-001',
            # Missing other fields
        }]
        
        with patch('src.data_extraction.sfdc_client.config', mock_config):
            client = SFDCClient()
            df = client._process_case_batch(test_records)
            
            assert len(df) == 1
            assert df.iloc[0]['Case_Number'] == 'TEST-001'
            # Missing fields should be handled gracefully (None or empty string)
            assert 'Subject_Description' in df.columns

    @patch('simple_salesforce.Salesforce')
    def test_connection_reuse(self, mock_sf, mock_config):
        """Test that connection is reused across method calls."""
        mock_sf_instance = Mock()
        mock_sf_instance.query.return_value = {'totalSize': 1, 'records': [{'Id': 'test'}]}
        mock_sf.return_value = mock_sf_instance
        
        with patch('src.data_extraction.sfdc_client.config', mock_config):
            client = SFDCClient()
            
            # First call should create connection
            client.test_connection()
            assert client.sf_client == mock_sf_instance
            
            # Second call should reuse connection
            client.test_connection()
            mock_sf.assert_called_once()  # Should only be called once

    def test_get_field_mapping_for_config(self, mock_config):
        """Test getting field mapping for specific config fields."""
        with patch('src.data_extraction.sfdc_client.config', mock_config):
            client = SFDCClient()
            
            config_fields = ['Case_Number', 'Subject_Description']
            mapping = client.get_field_mapping_for_config(config_fields)
            
            assert len(mapping) == 2
            assert mapping['Case_Number'] == 'Case_Number__c'
            assert mapping['Subject_Description'] == 'Subject_Description__c'

    def test_get_field_mapping_invalid_field(self, mock_config):
        """Test field mapping with invalid field."""
        with patch('src.data_extraction.sfdc_client.config', mock_config):
            client = SFDCClient()
            
            config_fields = ['Invalid_Field']
            mapping = client.get_field_mapping_for_config(config_fields)
            
            # Should handle invalid fields gracefully
            assert 'Invalid_Field' not in mapping or mapping['Invalid_Field'] is None