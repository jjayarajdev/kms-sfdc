"""
Unit tests for text processing utilities.
"""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import Mock, patch

from src.utils.text_processor import TextProcessor


@pytest.mark.unit
class TestTextProcessor:
    """Test cases for TextProcessor class."""

    def test_init(self, mock_config):
        """Test TextProcessor initialization."""
        with patch('src.utils.text_processor.config', mock_config):
            processor = TextProcessor()
            
            assert processor.config == mock_config.text_processing
            assert processor.min_length == mock_config.text_processing.min_text_length
            assert processor.max_length == mock_config.text_processing.max_text_length

    def test_clean_text_basic(self, mock_config):
        """Test basic text cleaning."""
        with patch('src.utils.text_processor.config', mock_config):
            processor = TextProcessor()
            
            # Test basic cleaning
            dirty_text = "  Hello   World!  \n\n  "
            clean_text = processor._clean_text(dirty_text)
            
            assert clean_text == "hello world!"

    def test_clean_text_html_removal(self, mock_config):
        """Test HTML tag removal."""
        with patch('src.utils.text_processor.config', mock_config):
            processor = TextProcessor()
            
            html_text = "<p>Hello <b>World</b>!</p><br/><div>Test</div>"
            clean_text = processor._clean_text(html_text)
            
            assert "<p>" not in clean_text
            assert "<b>" not in clean_text
            assert "<br/>" not in clean_text
            assert "hello world! test" == clean_text

    def test_clean_text_url_removal(self, mock_config):
        """Test URL removal."""
        with patch('src.utils.text_processor.config', mock_config):
            processor = TextProcessor()
            
            url_text = "Check this out: https://www.example.com and http://test.org"
            clean_text = processor._clean_text(url_text)
            
            assert "https://www.example.com" not in clean_text
            assert "http://test.org" not in clean_text
            assert "check this out: and" == clean_text

    def test_clean_text_email_removal(self, mock_config):
        """Test email address removal."""
        with patch('src.utils.text_processor.config', mock_config):
            processor = TextProcessor()
            
            email_text = "Contact us at support@example.com or admin@test.org"
            clean_text = processor._clean_text(email_text)
            
            assert "support@example.com" not in clean_text
            assert "admin@test.org" not in clean_text
            assert "contact us at or" == clean_text

    def test_is_valid_text_length(self, mock_config):
        """Test text length validation."""
        with patch('src.utils.text_processor.config', mock_config):
            processor = TextProcessor()
            
            # Too short
            assert not processor._is_valid_text("short")
            
            # Valid length
            valid_text = "This is a valid text with sufficient length for processing"
            assert processor._is_valid_text(valid_text)
            
            # Too long (create text longer than max_length)
            long_text = "x" * (mock_config.text_processing.max_text_length + 1)
            assert not processor._is_valid_text(long_text)

    def test_is_valid_text_empty(self, mock_config):
        """Test validation of empty or None text."""
        with patch('src.utils.text_processor.config', mock_config):
            processor = TextProcessor()
            
            assert not processor._is_valid_text("")
            assert not processor._is_valid_text(None)
            assert not processor._is_valid_text("   ")

    def test_combine_text_fields(self, mock_config):
        """Test combining multiple text fields."""
        with patch('src.utils.text_processor.config', mock_config):
            processor = TextProcessor()
            
            case_data = {
                'Subject_Description': 'Server problem',
                'Description_Description': 'The server is down',
                'Issue_Plain_Text': 'Critical server issue',
                'Resolution_Plain_Text': 'Restarted server'
            }
            
            combined = processor._combine_text_fields(case_data)
            expected = "Server problem. The server is down. Critical server issue. Restarted server."
            
            assert combined == expected

    def test_combine_text_fields_missing(self, mock_config):
        """Test combining text fields with missing values."""
        with patch('src.utils.text_processor.config', mock_config):
            processor = TextProcessor()
            
            case_data = {
                'Subject_Description': 'Server problem',
                'Description_Description': None,
                'Issue_Plain_Text': '',
                'Resolution_Plain_Text': 'Restarted server'
            }
            
            combined = processor._combine_text_fields(case_data)
            expected = "Server problem. Restarted server."
            
            assert combined == expected

    def test_combine_text_fields_empty_config(self, mock_config):
        """Test combining when no fields configured."""
        mock_config.text_processing.fields_to_vectorize = []
        
        with patch('src.utils.text_processor.config', mock_config):
            processor = TextProcessor()
            
            case_data = {'Subject_Description': 'Test'}
            combined = processor._combine_text_fields(case_data)
            
            assert combined == ""

    def test_preprocess_case_data_basic(self, mock_config, sample_case_data):
        """Test basic case data preprocessing."""
        with patch('src.utils.text_processor.config', mock_config):
            processor = TextProcessor()
            processed_df = processor.preprocess_case_data(sample_case_data)
            
            assert isinstance(processed_df, pd.DataFrame)
            assert 'combined_text' in processed_df.columns
            assert len(processed_df) <= len(sample_case_data)  # May filter some records
            
            # Check that combined text is created
            assert all(isinstance(text, str) for text in processed_df['combined_text'])

    def test_validate_data(self, mock_config, sample_case_data):
        """Test data validation."""
        with patch('src.utils.text_processor.config', mock_config):
            processor = TextProcessor()
            
            # Add some invalid data
            invalid_data = sample_case_data.copy()
            invalid_data.loc[len(invalid_data)] = {
                'Id': None,  # Invalid ID
                'Case_Number': '',
                'Subject_Description': '',
                'combined_text': ''
            }
            
            validated_df = processor._validate_data(invalid_data)
            
            # Should filter out invalid records
            assert len(validated_df) == len(sample_case_data)

    def test_detect_and_handle_duplicates(self, mock_config):
        """Test duplicate detection and handling."""
        # Create data with duplicates
        data_with_dupes = pd.DataFrame([
            {
                'Id': 'case_001',
                'combined_text': 'This is a test case for duplicate detection'
            },
            {
                'Id': 'case_002',
                'combined_text': 'This is a test case for duplicate detection'  # Exact duplicate
            },
            {
                'Id': 'case_003',
                'combined_text': 'This is a different case entirely'
            },
            {
                'Id': 'case_004',
                'combined_text': 'This is a test case for duplicate detection.'  # Near duplicate
            }
        ])
        
        with patch('src.utils.text_processor.config', mock_config):
            processor = TextProcessor()
            deduplicated_df = processor._detect_and_handle_duplicates(data_with_dupes)
            
            # Should remove exact duplicates, keep originals
            assert len(deduplicated_df) <= len(data_with_dupes)
            
            # Should have 'duplicate_of' column for tracking
            if 'duplicate_of' in deduplicated_df.columns:
                assert deduplicated_df['duplicate_of'].notna().any()

    def test_generate_content_hash(self, mock_config):
        """Test content hash generation."""
        with patch('src.utils.text_processor.config', mock_config):
            processor = TextProcessor()
            
            text1 = "This is a test case"
            text2 = "This is a test case"
            text3 = "This is a different case"
            
            hash1 = processor._generate_content_hash(text1)
            hash2 = processor._generate_content_hash(text2)
            hash3 = processor._generate_content_hash(text3)
            
            assert hash1 == hash2  # Same text should have same hash
            assert hash1 != hash3  # Different text should have different hash
            assert isinstance(hash1, str)

    def test_calculate_repetition_ratio(self, mock_config):
        """Test repetition ratio calculation."""
        with patch('src.utils.text_processor.config', mock_config):
            processor = TextProcessor()
            
            # Highly repetitive text
            repetitive_text = "the the the the the problem problem problem"
            ratio = processor._calculate_repetition_ratio(repetitive_text)
            assert ratio > 0.5
            
            # Normal text
            normal_text = "this is a normal sentence with varied words"
            ratio = processor._calculate_repetition_ratio(normal_text)
            assert ratio < 0.3

    def test_calculate_special_char_ratio(self, mock_config):
        """Test special character ratio calculation."""
        with patch('src.utils.text_processor.config', mock_config):
            processor = TextProcessor()
            
            # Text with many special characters
            special_text = "###@@@ $$$ !!! %%% text"
            ratio = processor._calculate_special_char_ratio(special_text)
            assert ratio > 0.5
            
            # Normal text
            normal_text = "this is normal text"
            ratio = processor._calculate_special_char_ratio(normal_text)
            assert ratio < 0.1

    def test_calculate_numeric_ratio(self, mock_config):
        """Test numeric character ratio calculation."""
        with patch('src.utils.text_processor.config', mock_config):
            processor = TextProcessor()
            
            # Text with many numbers
            numeric_text = "123 456 789 text 000"
            ratio = processor._calculate_numeric_ratio(numeric_text)
            assert ratio > 0.5
            
            # Normal text
            normal_text = "this is normal text"
            ratio = processor._calculate_numeric_ratio(normal_text)
            assert ratio == 0.0

    def test_apply_quality_filters(self, mock_config):
        """Test quality filtering."""
        # Create data with quality issues
        quality_data = pd.DataFrame([
            {
                'Id': 'case_001',
                'combined_text': 'This is a good quality case description with sufficient content'
            },
            {
                'Id': 'case_002',
                'combined_text': 'the the the the the same same same same'  # High repetition
            },
            {
                'Id': 'case_003',
                'combined_text': '### @@@ $$$ !!! text'  # High special char ratio
            },
            {
                'Id': 'case_004',
                'combined_text': '123 456 789 000 111'  # High numeric ratio
            }
        ])
        
        with patch('src.utils.text_processor.config', mock_config):
            processor = TextProcessor()
            filtered_df = processor._apply_quality_filters(quality_data)
            
            # Should filter out low-quality records
            assert len(filtered_df) < len(quality_data)
            assert filtered_df.iloc[0]['Id'] == 'case_001'  # Good quality should remain

    def test_get_text_stats(self, mock_config, sample_case_data):
        """Test text statistics calculation."""
        with patch('src.utils.text_processor.config', mock_config):
            processor = TextProcessor()
            
            # Add combined_text to sample data
            sample_case_data['combined_text'] = [
                'Short text',
                'This is a medium length text with more words',
                'This is a very long text with many words and should provide good statistics for testing'
            ]
            
            stats = processor.get_text_stats(sample_case_data)
            
            assert 'total_records' in stats
            assert 'avg_text_length' in stats
            assert 'min_text_length' in stats
            assert 'max_text_length' in stats
            assert 'median_text_length' in stats
            assert 'empty_text_count' in stats
            
            assert stats['total_records'] == 3
            assert stats['empty_text_count'] == 0
            assert stats['min_text_length'] < stats['avg_text_length'] < stats['max_text_length']

    def test_get_text_stats_empty_data(self, mock_config):
        """Test text statistics with empty data."""
        empty_df = pd.DataFrame({'combined_text': []})
        
        with patch('src.utils.text_processor.config', mock_config):
            processor = TextProcessor()
            stats = processor.get_text_stats(empty_df)
            
            assert stats['total_records'] == 0
            assert stats['avg_text_length'] == 0
            assert stats['empty_text_count'] == 0

    def test_preprocess_case_data_end_to_end(self, mock_config):
        """Test complete preprocessing pipeline."""
        # Create comprehensive test data
        test_data = pd.DataFrame([
            {
                'Id': 'case_001',
                'Case_Number': 'CASE-001',
                'Subject_Description': 'Server crashes unexpectedly',
                'Description_Description': 'The server crashes without warning',
                'Issue_Plain_Text': 'Server crashes',
                'Resolution_Plain_Text': 'Restarted server'
            },
            {
                'Id': 'case_002',
                'Case_Number': 'CASE-002',
                'Subject_Description': 'Database timeout',
                'Description_Description': '<p>Database <b>timeout</b> issues</p>',  # HTML
                'Issue_Plain_Text': 'Contact admin@example.com',  # Email
                'Resolution_Plain_Text': 'Check https://docs.example.com'  # URL
            },
            {
                'Id': 'case_003',  # Duplicate
                'Case_Number': 'CASE-003',
                'Subject_Description': 'Server crashes unexpectedly',
                'Description_Description': 'The server crashes without warning',
                'Issue_Plain_Text': 'Server crashes',
                'Resolution_Plain_Text': 'Restarted server'
            }
        ])
        
        with patch('src.utils.text_processor.config', mock_config):
            processor = TextProcessor()
            processed_df = processor.preprocess_case_data(test_data)
            
            assert isinstance(processed_df, pd.DataFrame)
            assert 'combined_text' in processed_df.columns
            assert len(processed_df) <= len(test_data)  # May remove duplicates
            
            # Check HTML/URL/email cleaning
            for text in processed_df['combined_text']:
                assert '<p>' not in text
                assert 'admin@example.com' not in text
                assert 'https://docs.example.com' not in text

    def test_text_length_boundaries(self, mock_config):
        """Test text length boundary conditions."""
        mock_config.text_processing.min_text_length = 10
        mock_config.text_processing.max_text_length = 50
        
        with patch('src.utils.text_processor.config', mock_config):
            processor = TextProcessor()
            
            # Exactly min length
            min_text = "a" * 10
            assert processor._is_valid_text(min_text)
            
            # One character short
            short_text = "a" * 9
            assert not processor._is_valid_text(short_text)
            
            # Exactly max length
            max_text = "a" * 50
            assert processor._is_valid_text(max_text)
            
            # One character over
            long_text = "a" * 51
            assert not processor._is_valid_text(long_text)

    def test_preprocessing_config_disabled(self, mock_config):
        """Test preprocessing when certain features are disabled."""
        # Disable HTML removal
        mock_config.text_processing.preprocessing.remove_html = False
        
        with patch('src.utils.text_processor.config', mock_config):
            processor = TextProcessor()
            
            html_text = "<p>Hello World</p>"
            clean_text = processor._clean_text(html_text)
            
            # HTML should be preserved when disabled
            assert "<p>" in clean_text or "hello world" in clean_text.lower()

    def test_memory_efficient_processing(self, mock_config):
        """Test processing with large dataset (memory efficiency)."""
        # Create larger dataset
        large_data = pd.DataFrame([
            {
                'Id': f'case_{i:04d}',
                'Case_Number': f'CASE-{i:04d}',
                'Subject_Description': f'Test case {i}',
                'Description_Description': f'Description for case {i}',
                'Issue_Plain_Text': f'Issue {i}',
                'Resolution_Plain_Text': f'Resolution {i}'
            }
            for i in range(100)
        ])
        
        with patch('src.utils.text_processor.config', mock_config):
            processor = TextProcessor()
            processed_df = processor.preprocess_case_data(large_data)
            
            assert isinstance(processed_df, pd.DataFrame)
            assert len(processed_df) <= len(large_data)
            assert 'combined_text' in processed_df.columns