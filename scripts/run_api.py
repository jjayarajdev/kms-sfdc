#!/usr/bin/env python3
"""Script to run the KMS-SFDC Vector Search API."""

import sys
import uvicorn
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent))

from src.utils.config import config
from src.search.api import app


def main():
    """Run the FastAPI server."""
    uvicorn.run(
        app,
        host=config.api.host,
        port=config.api.port,
        log_level="info",
        reload=False  # Set to True for development
    )


if __name__ == "__main__":
    main()