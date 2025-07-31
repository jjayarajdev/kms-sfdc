"""Text preprocessing utilities for KMS-SFDC Vector Database."""

import re
import hashlib
from typing import Dict, List, Optional, Set, Tuple
import pandas as pd
from loguru import logger
import numpy as np

from .config import config


class TextProcessor:
    """Handles text preprocessing for case data vectorization."""
    
    def __init__(self):
        """Initialize text processor with configuration."""
        self.config = config.text_processing
        self.preprocessing_config = self.config.preprocessing
    
    def preprocess_case_data(self, df: pd.DataFrame, detect_duplicates: bool = True, 
                            validate_data: bool = True) -> pd.DataFrame:
        """
        Preprocess case data DataFrame for vectorization with quality control.
        
        Args:
            df: DataFrame containing case data
            detect_duplicates: Whether to detect and handle duplicate cases
            validate_data: Whether to perform comprehensive data validation
            
        Returns:
            DataFrame with processed text fields and combined text column
        """
        logger.info(f"Preprocessing {len(df)} case records")
        
        processed_df = df.copy()
        
        # Perform data validation first
        if validate_data:
            processed_df = self._validate_data(processed_df)
        
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
        
        # Process each text field
        for config_field in self.config.fields_to_vectorize:
            # Map config field to actual SFDC field
            actual_field = field_mapping.get(config_field, config_field)
            
            if actual_field in processed_df.columns:
                processed_df[f"{actual_field}_processed"] = processed_df[actual_field].apply(
                    self._preprocess_text
                )
            else:
                logger.warning(f"Field {actual_field} (config: {config_field}) not found in data")
                processed_df[f"{actual_field}_processed"] = ""
        
        # Combine all text fields into single field for vectorization
        processed_df['combined_text'] = self._combine_text_fields(processed_df)
        
        # Filter out records with insufficient text
        initial_count = len(processed_df)
        processed_df = processed_df[
            processed_df['combined_text'].str.len() >= self.config.min_text_length
        ]
        
        # Detect and handle duplicates
        if detect_duplicates:
            processed_df = self._detect_and_handle_duplicates(processed_df)
        
        # Apply quality filters
        processed_df = self._apply_quality_filters(processed_df)
        
        final_count = len(processed_df)
        
        if final_count < initial_count:
            logger.info(f"Quality control filtered out {initial_count - final_count} records")
        
        return processed_df
    
    def _preprocess_text(self, text: Optional[str]) -> str:
        """
        Apply preprocessing steps to individual text field.
        
        Args:
            text: Raw text to preprocess
            
        Returns:
            Cleaned text
        """
        if not text or pd.isna(text):
            return ""
        
        text = str(text)
        
        # Remove HTML tags
        if self.preprocessing_config.get("remove_html", True):
            text = re.sub(r'<[^>]+>', ' ', text)
        
        # Remove URLs
        if self.preprocessing_config.get("remove_urls", True):
            text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', ' ', text)
        
        # Remove email addresses
        if self.preprocessing_config.get("remove_emails", True):
            text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', ' ', text)
        
        # Convert to lowercase
        if self.preprocessing_config.get("lowercase", True):
            text = text.lower()
        
        # Remove extra whitespace
        if self.preprocessing_config.get("remove_extra_whitespace", True):
            text = re.sub(r'\s+', ' ', text).strip()
        
        # Truncate if too long
        if len(text) > self.config.max_text_length:
            text = text[:self.config.max_text_length]
        
        return text
    
    def _combine_text_fields(self, df: pd.DataFrame) -> pd.Series:
        """
        Combine processed text fields into single text for vectorization.
        
        Args:
            df: DataFrame with processed text fields
            
        Returns:
            Series with combined text
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
        
        combined_texts = []
        
        for _, row in df.iterrows():
            text_parts = []
            
            for config_field in self.config.fields_to_vectorize:
                # Map config field to actual SFDC field
                actual_field = field_mapping.get(config_field, config_field)
                processed_field = f"{actual_field}_processed"
                
                if processed_field in row and row[processed_field]:
                    text_parts.append(str(row[processed_field]))
            
            combined_text = " ".join(text_parts)
            combined_texts.append(combined_text)
        
        return pd.Series(combined_texts, index=df.index)
    
    def extract_keywords(self, text: str, max_keywords: int = 10) -> List[str]:
        """
        Extract key terms from text (simple implementation).
        
        Args:
            text: Input text
            max_keywords: Maximum number of keywords to return
            
        Returns:
            List of extracted keywords
        """
        if not text:
            return []
        
        # Simple keyword extraction - can be enhanced with NLP libraries
        words = text.lower().split()
        
        # Filter out short words and common stop words
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have',
            'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should',
            'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they'
        }
        
        keywords = [
            word for word in words 
            if len(word) > 3 and word not in stop_words and word.isalpha()
        ]
        
        # Count frequency and return most common
        word_freq = {}
        for word in keywords:
            word_freq[word] = word_freq.get(word, 0) + 1
        
        sorted_keywords = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        return [word for word, freq in sorted_keywords[:max_keywords]]
    
    def get_text_stats(self, df: pd.DataFrame) -> Dict:
        """
        Get statistics about text data in DataFrame.
        
        Args:
            df: DataFrame with text data
            
        Returns:
            Dictionary with text statistics
        """
        if 'combined_text' not in df.columns:
            return {}
        
        text_lengths = df['combined_text'].str.len()
        
        stats = {
            'total_records': len(df),
            'avg_text_length': text_lengths.mean(),
            'min_text_length': text_lengths.min(),
            'max_text_length': text_lengths.max(),
            'median_text_length': text_lengths.median(),
            'empty_text_count': (text_lengths == 0).sum()
        }
        
        logger.info(f"Text statistics: {stats}")
        return stats
    
    def _validate_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Perform comprehensive data validation.
        
        Args:
            df: DataFrame to validate
            
        Returns:
            Validated DataFrame with issues logged
        """
        logger.info("Performing data validation...")
        initial_count = len(df)
        
        # Check for required fields
        required_fields = ['Id', 'CaseNumber']
        missing_fields = [field for field in required_fields if field not in df.columns]
        if missing_fields:
            logger.error(f"Missing required fields: {missing_fields}")
            raise ValueError(f"Missing required fields: {missing_fields}")
        
        # Remove rows with null IDs or CaseNumbers
        df = df.dropna(subset=['Id', 'CaseNumber'])
        
        # Validate date fields if present
        if 'CreatedDate' in df.columns:
            # Convert to datetime and validate
            try:
                df['CreatedDate'] = pd.to_datetime(df['CreatedDate'], errors='coerce')
                invalid_dates = df['CreatedDate'].isna().sum()
                if invalid_dates > 0:
                    logger.warning(f"Found {invalid_dates} records with invalid dates")
            except Exception as e:
                logger.warning(f"Date validation error: {e}")
        
        # Check for data consistency
        if 'Status' in df.columns:
            valid_statuses = ['New', 'Working', 'Escalated', 'Closed', 'Resolved']
            invalid_status = ~df['Status'].isin(valid_statuses + [None, np.nan])
            if invalid_status.any():
                logger.warning(f"Found {invalid_status.sum()} records with invalid status")
        
        # Log validation results
        removed_count = initial_count - len(df)
        if removed_count > 0:
            logger.info(f"Data validation removed {removed_count} invalid records")
        
        return df
    
    def _detect_and_handle_duplicates(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Detect and handle duplicate cases based on content similarity.
        
        Args:
            df: DataFrame with combined_text column
            
        Returns:
            DataFrame with duplicates handled
        """
        logger.info("Detecting duplicate cases...")
        
        # Method 1: Exact text duplicates
        exact_duplicates = df.duplicated(subset=['combined_text'], keep='first')
        exact_dup_count = exact_duplicates.sum()
        
        if exact_dup_count > 0:
            logger.info(f"Found {exact_dup_count} exact text duplicates")
            df = df[~exact_duplicates]
        
        # Method 2: Near-duplicate detection using content hashing
        df['content_hash'] = df['combined_text'].apply(self._generate_content_hash)
        
        # Group by hash and keep the most recent case
        if 'CreatedDate' in df.columns:
            df = df.sort_values('CreatedDate', ascending=False)
        
        hash_duplicates = df.duplicated(subset=['content_hash'], keep='first')
        hash_dup_count = hash_duplicates.sum()
        
        if hash_dup_count > 0:
            logger.info(f"Found {hash_dup_count} near-duplicates by content hash")
            df = df[~hash_duplicates]
        
        # Drop the temporary hash column
        df = df.drop(columns=['content_hash'])
        
        # Method 3: Case ID duplicates (shouldn't happen but check anyway)
        if 'Id' in df.columns:
            id_duplicates = df.duplicated(subset=['Id'], keep='first')
            if id_duplicates.any():
                logger.warning(f"Found {id_duplicates.sum()} duplicate case IDs")
                df = df[~id_duplicates]
        
        return df
    
    def _generate_content_hash(self, text: str) -> str:
        """
        Generate a hash for near-duplicate detection.
        Normalizes text to catch similar content.
        
        Args:
            text: Text to hash
            
        Returns:
            Content hash string
        """
        if not text:
            return ""
        
        # Normalize for near-duplicate detection
        normalized = text.lower()
        # Remove extra whitespace and punctuation for similarity
        normalized = re.sub(r'[^\w\s]', '', normalized)
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        
        # Take first 1000 chars for hash (to catch similar beginnings)
        normalized = normalized[:1000]
        
        # Generate hash
        return hashlib.md5(normalized.encode()).hexdigest()
    
    def _apply_quality_filters(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Apply quality filters to remove low-quality records.
        
        Args:
            df: DataFrame with combined_text
            
        Returns:
            Filtered DataFrame
        """
        logger.info("Applying quality filters...")
        initial_count = len(df)
        
        # Filter 1: Remove cases with too much repetitive content
        df['repetition_score'] = df['combined_text'].apply(self._calculate_repetition_score)
        high_repetition = df['repetition_score'] > 0.7  # More than 70% repetitive
        if high_repetition.any():
            logger.info(f"Removing {high_repetition.sum()} cases with high repetition")
            df = df[~high_repetition]
        
        # Filter 2: Remove cases with too many special characters (likely corrupted)
        df['special_char_ratio'] = df['combined_text'].apply(self._calculate_special_char_ratio)
        high_special = df['special_char_ratio'] > 0.3  # More than 30% special chars
        if high_special.any():
            logger.info(f"Removing {high_special.sum()} cases with excessive special characters")
            df = df[~high_special]
        
        # Filter 3: Remove cases that are mostly numbers/codes
        df['numeric_ratio'] = df['combined_text'].apply(self._calculate_numeric_ratio)
        high_numeric = df['numeric_ratio'] > 0.5  # More than 50% numeric
        if high_numeric.any():
            logger.info(f"Removing {high_numeric.sum()} cases that are mostly numeric")
            df = df[~high_numeric]
        
        # Filter 4: Ensure minimum word count
        df['word_count'] = df['combined_text'].str.split().str.len()
        too_few_words = df['word_count'] < 5  # Less than 5 words
        if too_few_words.any():
            logger.info(f"Removing {too_few_words.sum()} cases with too few words")
            df = df[~too_few_words]
        
        # Clean up temporary columns
        df = df.drop(columns=['repetition_score', 'special_char_ratio', 'numeric_ratio', 'word_count'])
        
        final_count = len(df)
        if final_count < initial_count:
            logger.info(f"Quality filters removed {initial_count - final_count} low-quality records")
        
        return df
    
    def _calculate_repetition_score(self, text: str) -> float:
        """Calculate how repetitive the text is."""
        if not text or len(text) < 10:
            return 0.0
        
        # Check for repeated words
        words = text.lower().split()
        if not words:
            return 0.0
        
        unique_words = set(words)
        repetition = 1.0 - (len(unique_words) / len(words))
        
        # Check for repeated characters
        chars = text.lower()
        char_counts = {}
        for char in chars:
            if char.isalpha():
                char_counts[char] = char_counts.get(char, 0) + 1
        
        if char_counts:
            max_char_ratio = max(char_counts.values()) / len([c for c in chars if c.isalpha()])
            repetition = max(repetition, max_char_ratio)
        
        return repetition
    
    def _calculate_special_char_ratio(self, text: str) -> float:
        """Calculate ratio of special characters in text."""
        if not text:
            return 0.0
        
        special_chars = sum(1 for c in text if not c.isalnum() and not c.isspace())
        return special_chars / len(text)
    
    def _calculate_numeric_ratio(self, text: str) -> float:
        """Calculate ratio of numeric characters in text."""
        if not text:
            return 0.0
        
        numeric_chars = sum(1 for c in text if c.isdigit())
        return numeric_chars / len(text)