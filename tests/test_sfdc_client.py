"""Tests for SFDC client module."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import pandas as pd

from src.data_extraction.sfdc_client import SFDCClient


class TestSFDCClient:
    """Test cases for SFDCClient."""
    
    @pytest.fixture
    def mock_sf(self):
        """Mock Salesforce connection."""
        with patch('src.data_extraction.sfdc_client.Salesforce') as mock:
            yield mock
    
    @pytest.fixture
    def client(self, mock_sf):
        """Create SFDCClient instance with mocked connection."""
        return SFDCClient()
    
    def test_connection_initialization(self, mock_sf):
        """Test Salesforce connection initialization."""
        client = SFDCClient()
        assert client.sf is not None
        mock_sf.assert_called_once()
    
    def test_connection_failure(self, mock_sf):
        """Test handling of connection failure."""
        mock_sf.side_effect = Exception("Connection failed")
        
        with pytest.raises(Exception, match="Connection failed"):
            SFDCClient()
    
    def test_get_case_data(self, client):
        """Test case data extraction."""
        # Mock query result
        mock_records = [
            {
                'Id': '500XX0000001',
                'CaseNumber': '00001000',
                'Subject': 'Test issue',
                'Description': 'Test description',
                'Status': 'Open'
            },
            {
                'Id': '500XX0000002', 
                'CaseNumber': '00001001',
                'Subject': 'Another issue',
                'Description': 'Another description',
                'Status': 'Closed'
            }
        ]
        
        client.sf.query_all.return_value = {'records': mock_records}
        
        # Test data extraction
        df = client.get_case_data()
        
        assert len(df) == 2
        assert 'Id' in df.columns
        assert 'CaseNumber' in df.columns
        assert df.iloc[0]['Subject'] == 'Test issue'
    
    def test_get_case_data_with_dates(self, client):
        """Test case data extraction with specific date range."""
        client.sf.query_all.return_value = {'records': []}
        
        start_date = datetime(2022, 1, 1)
        end_date = datetime(2023, 1, 1)
        
        client.get_case_data(start_date=start_date, end_date=end_date)
        
        # Verify query was called
        client.sf.query_all.assert_called_once()
        query_arg = client.sf.query_all.call_args[0][0]
        assert '2022-01-01T00:00:00.000+0000' in query_arg
        assert '2023-01-01T00:00:00.000+0000' in query_arg
    
    def test_batch_extraction(self, client):
        """Test batch data extraction."""
        # Mock batch query results
        batch1_records = [{'Id': '1', 'Subject': 'First'}]
        batch2_records = [{'Id': '2', 'Subject': 'Second'}]
        
        # First call returns batch 1
        client.sf.query.return_value = {
            'records': batch1_records,
            'done': False,
            'nextRecordsUrl': '/next_batch'
        }
        
        # Second call returns batch 2
        client.sf.query_more.return_value = {
            'records': batch2_records,
            'done': True
        }
        
        # Test batch extraction
        batches = list(client.get_case_data_batch())
        
        assert len(batches) == 2
        assert len(batches[0]) == 1
        assert len(batches[1]) == 1
        assert batches[0].iloc[0]['Subject'] == 'First'
        assert batches[1].iloc[0]['Subject'] == 'Second'
    
    def test_build_case_query(self, client):
        """Test SOQL query building."""
        start_date = datetime(2022, 1, 1)
        end_date = datetime(2023, 1, 1)
        
        query = client._build_case_query(start_date, end_date)
        
        assert 'SELECT' in query
        assert 'FROM Case' in query
        assert 'WHERE CreatedDate >=' in query
        assert '2022-01-01T00:00:00.000+0000' in query
        assert '2023-01-01T00:00:00.000+0000' in query
        assert 'ORDER BY CreatedDate DESC' in query
    
    def test_get_case_fields_info(self, client):
        """Test case fields metadata retrieval."""
        mock_describe = {
            'fields': [
                {
                    'name': 'Id',
                    'label': 'Case ID',
                    'type': 'id',
                    'length': 18,
                    'custom': False
                },
                {
                    'name': 'Subject',
                    'label': 'Subject',
                    'type': 'string',
                    'length': 255,
                    'custom': False
                }
            ]
        }
        
        client.sf.Case.describe.return_value = mock_describe
        
        fields_info = client.get_case_fields_info()
        
        assert 'Id' in fields_info
        assert 'Subject' in fields_info
        assert fields_info['Id']['label'] == 'Case ID'
        assert fields_info['Subject']['type'] == 'string'
    
    def test_connection_test_success(self, client):
        """Test successful connection test."""
        client.sf.query.return_value = {'records': [{'Id': '123'}]}
        
        result = client.test_connection()
        
        assert result is True
        client.sf.query.assert_called_once_with("SELECT Id FROM Case LIMIT 1")
    
    def test_connection_test_failure(self, client):
        """Test failed connection test."""
        client.sf.query.side_effect = Exception("Connection error")
        
        result = client.test_connection()
        
        assert result is False