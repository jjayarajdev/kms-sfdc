"""Configuration management for KMS-SFDC Vector Database."""

import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field


class SalesforceConfig(BaseModel):
    username: str
    password: str
    security_token: str
    login_url: str = "https://login.salesforce.com/"
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    api_version: str = "58.0"
    query_batch_size: int = 2000
    max_records: Optional[int] = None
    date_range_years: int = 2


class VectorDBConfig(BaseModel):
    model_config = {'protected_namespaces': ()}
    
    model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_dimension: int = 384
    faiss_index_type: str = "IndexIVFPQ"
    batch_size: int = 1000
    # Production scale settings
    embedding_batch_size: int = 5000
    indexing_batch_size: int = 50000
    daily_update_batch_size: int = 10000
    nlist: int = 4096
    m: int = 64
    nbits: int = 8
    search_nprobe: int = 128
    # Paths
    index_path: str = "data/faiss_index.bin"
    metadata_path: str = "data/case_metadata.json"
    temp_index_path: str = "data/temp_index.bin"
    backup_index_path: str = "data/backup_index.bin"
    # Additional settings
    incremental_merge_threshold: int = 100000
    use_gpu: bool = False
    memory_mapping: bool = True
    precompute_table: bool = True
    parallel_threads: int = 8
    chunk_size_mb: int = 1024


class TextProcessingConfig(BaseModel):
    min_text_length: int = 10
    max_text_length: int = 10000
    fields_to_vectorize: list[str] = Field(
          default=[
            "Case_Number",
            "Subject_Description",
            "Description_Description",
            "Issue_Plain_Text",
            "Cause_Plain_Text",
            "Resolution_Plain_Text",
            "Status_Text",
            "TextBody",
            "Description_Summary",
            "Comment_Body_Text"
        ])
    preprocessing: Dict[str, bool] = Field(
        default={
            "remove_html": True,
            "remove_urls": True,
            "remove_emails": True,
            "lowercase": True,
            "remove_extra_whitespace": True,
        }
    )


class SearchConfig(BaseModel):
    default_top_k: int = 10
    similarity_threshold: float = 0.7
    max_results: int = 50


class APIConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8000
    title: str = "KMS SFDC Vector Search API"
    version: str = "1.0.0"


class LoggingConfig(BaseModel):
    level: str = "INFO"
    format: str = "{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} | {message}"


class MonitoringConfig(BaseModel):
    enable_metrics: bool = True
    metrics_port: int = 9090


class Config(BaseModel):
    salesforce: SalesforceConfig
    vectordb: VectorDBConfig
    text_processing: TextProcessingConfig
    search: SearchConfig
    api: APIConfig
    logging: LoggingConfig
    monitoring: MonitoringConfig


def load_config(config_path: Optional[str] = None) -> Config:
    """Load configuration from YAML file with environment variable substitution."""
    
    # Load environment variables
    load_dotenv()
    
    # Default config path
    if config_path is None:
        config_path = Path(__file__).parent.parent.parent / "config" / "config.yaml"
    
    # Load YAML config
    with open(config_path, "r") as f:
        config_data = yaml.safe_load(f)
    
    # Substitute environment variables
    config_data = _substitute_env_vars(config_data)
    
    return Config(**config_data)


def _substitute_env_vars(obj: Any) -> Any:
    """Recursively substitute ${VAR_NAME:default} patterns with environment variables."""
    if isinstance(obj, dict):
        return {key: _substitute_env_vars(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [_substitute_env_vars(item) for item in obj]
    elif isinstance(obj, str) and obj.startswith("${") and obj.endswith("}"):
        # Parse ${VAR_NAME:default_value} format
        var_spec = obj[2:-1]  # Remove ${ and }
        if ":" in var_spec:
            var_name, default_value = var_spec.split(":", 1)
        else:
            var_name, default_value = var_spec, None
        
        return os.getenv(var_name, default_value)
    else:
        return obj


# Global config instance
config = load_config()