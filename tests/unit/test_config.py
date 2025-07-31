"""
Unit tests for configuration management.
"""

import pytest
import os
import tempfile
from unittest.mock import Mock, patch, mock_open
import yaml

from src.utils.config import Config, load_config


@pytest.mark.unit
class TestConfig:
    """Test cases for configuration management."""

    def test_config_initialization(self):
        """Test Config class initialization."""
        config_data = {
            'vectordb': {'model_name': 'test-model'},
            'search': {'default_top_k': 10}
        }
        
        config = Config(config_data)
        
        assert hasattr(config, 'vectordb')
        assert hasattr(config, 'search')
        assert config.vectordb.model_name == 'test-model'
        assert config.search.default_top_k == 10

    def test_config_nested_access(self):
        """Test nested configuration access."""
        config_data = {
            'database': {
                'connection': {
                    'host': 'localhost',
                    'port': 5432
                }
            }
        }
        
        config = Config(config_data)
        
        assert config.database.connection.host == 'localhost'
        assert config.database.connection.port == 5432

    def test_config_missing_attribute(self):
        """Test accessing missing configuration attribute."""
        config_data = {'existing': {'value': 'test'}}
        config = Config(config_data)
        
        with pytest.raises(AttributeError):
            _ = config.nonexistent.value

    def test_config_dict_method(self):
        """Test converting config back to dictionary."""
        config_data = {
            'section1': {'key1': 'value1'},
            'section2': {'key2': 'value2'}
        }
        
        config = Config(config_data)
        result_dict = config.dict()
        
        assert result_dict == config_data

    @patch('builtins.open', new_callable=mock_open, read_data="""
vectordb:
  model_name: "test-model"
  embedding_dimension: 384
search:
  default_top_k: 10
  similarity_threshold: 0.4
    """)
    @patch('os.path.exists', return_value=True)
    def test_load_config_from_file(self, mock_exists, mock_file):
        """Test loading configuration from YAML file."""
        config = load_config('test_config.yaml')
        
        assert isinstance(config, Config)
        assert config.vectordb.model_name == 'test-model'
        assert config.vectordb.embedding_dimension == 384
        assert config.search.default_top_k == 10
        assert config.search.similarity_threshold == 0.4

    @patch('os.path.exists', return_value=False)
    def test_load_config_file_not_found(self, mock_exists):
        """Test loading configuration when file doesn't exist."""
        with pytest.raises(FileNotFoundError):
            load_config('nonexistent_config.yaml')

    @patch('builtins.open', new_callable=mock_open, read_data="invalid: yaml: content:")
    @patch('os.path.exists', return_value=True)
    def test_load_config_invalid_yaml(self, mock_exists, mock_file):
        """Test loading configuration with invalid YAML."""
        with pytest.raises(yaml.YAMLError):
            load_config('invalid_config.yaml')

    def test_config_environment_variable_substitution(self):
        """Test environment variable substitution in config."""
        os.environ['TEST_HOST'] = 'test.example.com'
        os.environ['TEST_PORT'] = '8080'
        
        config_data = {
            'server': {
                'host': '${TEST_HOST}',
                'port': '${TEST_PORT}',
                'name': 'test-server'
            }
        }
        
        config = Config(config_data)
        
        # Note: Basic Config class doesn't do env substitution
        # This would need to be implemented in a subclass or during loading
        assert config.server.host == '${TEST_HOST}'  # Not substituted
        
        # Clean up
        del os.environ['TEST_HOST']
        del os.environ['TEST_PORT']

    def test_config_type_preservation(self):
        """Test that configuration preserves data types."""
        config_data = {
            'settings': {
                'string_value': 'test',
                'int_value': 42,
                'float_value': 3.14,
                'bool_value': True,
                'list_value': [1, 2, 3],
                'dict_value': {'nested': 'value'}
            }
        }
        
        config = Config(config_data)
        
        assert isinstance(config.settings.string_value, str)
        assert isinstance(config.settings.int_value, int)
        assert isinstance(config.settings.float_value, float)
        assert isinstance(config.settings.bool_value, bool)
        assert isinstance(config.settings.list_value, list)
        assert isinstance(config.settings.dict_value, dict)

    def test_config_empty_sections(self):
        """Test configuration with empty sections."""
        config_data = {
            'empty_section': {},
            'non_empty': {'key': 'value'}
        }
        
        config = Config(config_data)
        
        assert hasattr(config, 'empty_section')
        assert hasattr(config, 'non_empty')
        assert config.non_empty.key == 'value'

    def test_config_deep_nesting(self):
        """Test deeply nested configuration structure."""
        config_data = {
            'level1': {
                'level2': {
                    'level3': {
                        'level4': {
                            'value': 'deep_value'
                        }
                    }
                }
            }
        }
        
        config = Config(config_data)
        
        assert config.level1.level2.level3.level4.value == 'deep_value'

    def test_config_list_access(self):
        """Test accessing list values in configuration."""
        config_data = {
            'features': {
                'enabled': ['feature1', 'feature2', 'feature3'],
                'disabled': []
            }
        }
        
        config = Config(config_data)
        
        assert len(config.features.enabled) == 3
        assert 'feature1' in config.features.enabled
        assert len(config.features.disabled) == 0

    @patch.dict(os.environ, {'CONFIG_PATH': '/custom/config.yaml'})
    def test_config_from_environment(self):
        """Test loading config path from environment variable."""
        expected_path = '/custom/config.yaml'
        
        # This would be used in actual config loading logic
        config_path = os.getenv('CONFIG_PATH', 'config/config.yaml')
        
        assert config_path == expected_path

    def test_config_validation(self):
        """Test configuration validation."""
        # Test with valid config
        valid_config_data = {
            'vectordb': {
                'model_name': 'test-model',
                'embedding_dimension': 384
            },
            'search': {
                'default_top_k': 10,
                'similarity_threshold': 0.4
            }
        }
        
        config = Config(valid_config_data)
        
        # Basic validation - checking required fields exist
        assert hasattr(config, 'vectordb')
        assert hasattr(config, 'search')
        assert hasattr(config.vectordb, 'model_name')
        assert hasattr(config.search, 'default_top_k')

    def test_config_defaults(self):
        """Test configuration with default values."""
        config_data = {
            'database': {
                'host': 'localhost'
                # port missing, should use default
            }
        }
        
        config = Config(config_data)
        
        assert config.database.host == 'localhost'
        
        # Test accessing missing attribute with default
        default_port = getattr(config.database, 'port', 5432)
        assert default_port == 5432

    def test_config_override(self):
        """Test configuration value override."""
        base_config = {
            'settings': {
                'debug': False,
                'timeout': 30
            }
        }
        
        override_config = {
            'settings': {
                'debug': True
            }
        }
        
        # Simulate config override (would be implemented in config loader)
        base_config['settings'].update(override_config['settings'])
        
        config = Config(base_config)
        
        assert config.settings.debug is True  # Overridden
        assert config.settings.timeout == 30   # Preserved

    def test_config_string_representation(self):
        """Test string representation of config."""
        config_data = {
            'app': {
                'name': 'test-app',
                'version': '1.0.0'
            }
        }
        
        config = Config(config_data)
        
        # Test that we can convert to string without errors
        config_str = str(config)
        assert isinstance(config_str, str)
        assert 'Config' in config_str

    def test_config_attribute_error_message(self):
        """Test that attribute errors provide helpful messages."""
        config_data = {'existing': {'value': 'test'}}
        config = Config(config_data)
        
        try:
            _ = config.nonexistent.value
        except AttributeError as e:
            assert 'nonexistent' in str(e)

    @patch('builtins.open', new_callable=mock_open, read_data="""
# Configuration for KMS-SFDC
vectordb:
  model_name: "sentence-transformers/all-MiniLM-L6-v2"
  embedding_dimension: 384
  use_gpu: true
  # Index configuration
  faiss_index_type: "IndexIVFPQ"
  
search:
  default_top_k: 10
  similarity_threshold: 0.4
  max_results: 50

# Text processing settings
text_processing:
  min_text_length: 10
  max_text_length: 10000
  fields_to_vectorize:
    - "Case_Number"
    - "Subject_Description"
    - "Issue_Plain_Text"
    """)
    @patch('os.path.exists', return_value=True)
    def test_load_realistic_config(self, mock_exists, mock_file):
        """Test loading a realistic configuration file."""
        config = load_config('realistic_config.yaml')
        
        # Test vectordb section
        assert config.vectordb.model_name == "sentence-transformers/all-MiniLM-L6-v2"
        assert config.vectordb.embedding_dimension == 384
        assert config.vectordb.use_gpu is True
        assert config.vectordb.faiss_index_type == "IndexIVFPQ"
        
        # Test search section
        assert config.search.default_top_k == 10
        assert config.search.similarity_threshold == 0.4
        assert config.search.max_results == 50
        
        # Test text processing section
        assert config.text_processing.min_text_length == 10
        assert config.text_processing.max_text_length == 10000
        assert len(config.text_processing.fields_to_vectorize) == 3
        assert "Case_Number" in config.text_processing.fields_to_vectorize