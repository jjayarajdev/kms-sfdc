#!/usr/bin/env python3
"""
Standalone script for cron-based SFDC synchronization.
Can be used as an alternative to the built-in scheduler.

Usage:
    python sync_cron.py [--start-date YYYY-MM-DD] [--end-date YYYY-MM-DD]

Crontab example for hourly sync:
    0 * * * * /opt/kms-sfdc/venv/bin/python /opt/kms-sfdc/scripts/sync_cron.py >> /opt/kms-sfdc/logs/sync_cron.log 2>&1
"""

import sys
import argparse
import logging
from datetime import datetime, timedelta
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent))

from src.scheduler.sync_job import SFDCDataSyncJob


def setup_logging():
    """Set up logging for cron execution."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger(__name__)


def main():
    """Main function for cron-based sync."""
    parser = argparse.ArgumentParser(description="Run SFDC data synchronization")
    parser.add_argument("--start-date", type=str, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end-date", type=str, help="End date (YYYY-MM-DD)")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be synced without executing")
    
    args = parser.parse_args()
    logger = setup_logging()
    
    logger.info("=" * 60)
    logger.info("Starting SFDC sync job via cron")
    logger.info(f"Timestamp: {datetime.utcnow().isoformat()}")
    
    try:
        # Initialize sync job
        sync_job = SFDCDataSyncJob()
        
        if args.dry_run:
            # Just validate and show what would be done
            logger.info("DRY RUN MODE - No changes will be made")
            
            validation = sync_job.validate_sync()
            logger.info(f"Validation result: {validation}")
            
            start_date, end_date = sync_job.calculate_sync_window()
            logger.info(f"Would sync from {start_date} to {end_date}")
            
            stats = sync_job.get_sync_stats()
            logger.info(f"Current stats: {stats}")
        else:
            # Run actual sync
            result = sync_job.run()
            
            # Log results
            logger.info(f"Sync completed with status: {result['status']}")
            logger.info(f"Cases extracted: {result['cases_extracted']}")
            logger.info(f"Cases processed: {result['cases_processed']}")
            logger.info(f"Cases added: {result['cases_added']}")
            logger.info(f"Duration: {result.get('duration_seconds', 0):.2f} seconds")
            
            if result['status'] == 'error':
                logger.error(f"Sync failed with error: {result.get('error')}")
                sys.exit(1)
        
        logger.info("Sync job completed successfully")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"Fatal error during sync: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()