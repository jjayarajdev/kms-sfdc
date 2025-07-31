# SFDC Data Scheduler Guide

This guide explains how to configure and use the automated SFDC data synchronization scheduler in the KMS-SFDC system.

## Overview

The scheduler system provides automated, configurable synchronization of Salesforce case data to keep the vector database up-to-date with the latest cases. It supports:

- **Hourly intervals** (configurable from 1 minute to 24 hours)
- **Daily scheduled runs** at specific times
- **Manual trigger** for on-demand synchronization
- **UI-based configuration** through the admin dashboard

## Architecture

### Components

1. **Scheduler Service** (`src/scheduler/scheduler_service.py`)
   - Manages scheduled jobs
   - Handles job execution timing
   - Stores configuration in JSON format
   - Runs in background thread

2. **SFDC Sync Job** (`src/scheduler/sync_job.py`)
   - Extracts new/updated cases from Salesforce
   - Processes text data
   - Updates vector database incrementally
   - Handles errors and rollback

3. **API Endpoints** (`src/search/api.py`)
   - `/scheduler/jobs` - List all scheduled jobs
   - `/scheduler/jobs/{job_id}` - Get/update specific job
   - `/sync/status` - Current sync status
   - `/sync/history` - Sync history

4. **UI Components** (`admin-ui/src/components/SchedulerConfig.jsx`)
   - Visual scheduler configuration
   - Real-time status monitoring
   - Manual sync trigger
   - History viewer

## Configuration

### Initial Setup

1. **Default Configuration**
   - Hourly sync is configured by default
   - Stored in `data/scheduler_config.json`
   - Can be modified through UI or API

2. **Environment Variables**
   - Uses same SFDC credentials from `.env`
   - No additional configuration needed

### Schedule Types

#### Interval Schedule
```json
{
  "type": "interval",
  "interval_minutes": 60
}
```

#### Daily Schedule
```json
{
  "type": "daily",
  "time": "02:00"
}
```

#### Cron Expression (Future)
```json
{
  "type": "cron",
  "expression": "0 */2 * * *"
}
```

## Using the Scheduler

### Via Admin UI

1. Navigate to `http://localhost:3000/scheduler`
2. View current sync status and schedule
3. Click "Configure" to modify schedule:
   - Toggle Enable/Disable
   - Select schedule type
   - Set interval or time
4. Click "Manual Sync" for immediate sync

### Via API

#### Get Current Schedule
```bash
curl http://localhost:8008/scheduler/jobs
```

#### Update Schedule
```bash
curl -X PUT http://localhost:8008/scheduler/jobs/sfdc_sync \
  -H "Content-Type: application/json" \
  -d '{
    "enabled": true,
    "schedule": {
      "type": "interval",
      "interval_minutes": 120
    }
  }'
```

#### Trigger Manual Sync
```bash
curl -X POST http://localhost:8008/sync/manual
```

#### Check Sync Status
```bash
curl http://localhost:8008/sync/status
```

## Monitoring

### Sync Status Indicators

- **Last Sync**: Timestamp of last sync attempt
- **Last Successful Sync**: Timestamp of last successful completion
- **Total Cases**: Current number of cases in index
- **Average Duration**: Average time for sync operations

### Validation Checks

The system performs automatic validation:
- SFDC connection availability
- Vector database health
- Time since last sync (warns if >24 hours)

### Sync History

View recent sync operations:
- Cases processed
- Cases added
- Duration
- Success/failure status

## How It Works

### Incremental Sync Process

1. **Calculate Time Window**
   - From: Last successful sync time (minus 5-minute overlap)
   - To: Current time
   - First sync: Configured date range (default 2 years)

2. **Extract Data**
   - Query SFDC for cases in time window
   - Batch processing for large datasets
   - Uses SOQL with CreatedDate/LastModifiedDate filters

3. **Process Data**
   - Text preprocessing and cleaning
   - Quality filtering
   - Duplicate detection

4. **Update Index**
   - Incremental update for existing index
   - Only adds new cases (no updates yet)
   - Saves updated index and metadata

5. **Error Handling**
   - Creates backup before update
   - Restores on failure
   - Logs all operations

### State Management

Sync state stored in `data/sync_state.json`:
```json
{
  "last_sync_time": "2024-01-20T10:30:00",
  "last_successful_sync": "2024-01-20T10:30:00",
  "total_cases_synced": 150000,
  "total_cases_in_index": 150000,
  "sync_history": [...]
}
```

## Best Practices

### Scheduling Recommendations

1. **Hourly Sync** (Default)
   - Good for most use cases
   - Balances freshness with resource usage
   - Recommended: Every 1-2 hours

2. **Daily Sync**
   - For lower-volume environments
   - Schedule during off-peak hours
   - Recommended: 2:00 AM local time

3. **High-Frequency Sync**
   - For critical environments
   - Consider resource impact
   - Minimum: 15 minutes

### Performance Considerations

- Each sync processes only new/modified cases
- Batch size: 2000 cases (configurable)
- Average sync time: 2-5 minutes for hourly updates
- Full rebuild: Use manual trigger during maintenance

### Monitoring Guidelines

1. **Check Daily**
   - Sync status in admin UI
   - Any validation warnings
   - Sync history for failures

2. **Alert Conditions**
   - Last sync >24 hours old
   - Multiple consecutive failures
   - Sync duration >30 minutes

3. **Maintenance**
   - Review sync history weekly
   - Clean old backups monthly
   - Monitor index growth

## Troubleshooting

### Common Issues

1. **Sync Fails to Start**
   - Check SFDC credentials in `.env`
   - Verify scheduler is enabled
   - Check API logs for errors

2. **Sync Takes Too Long**
   - Check SFDC query performance
   - Reduce batch size if needed
   - Consider more frequent syncs

3. **Index Not Updating**
   - Verify write permissions on data directory
   - Check available disk space
   - Review text processing logs

### Debug Commands

```bash
# Check scheduler status
curl http://localhost:8008/scheduler/jobs

# View sync validation
curl http://localhost:8008/sync/status

# Check recent sync history
curl http://localhost:8008/sync/history?limit=20

# View API logs
tail -f logs/api_*.log
```

### Recovery Procedures

1. **Failed Sync Recovery**
   - System auto-restores from backup
   - Check logs for root cause
   - Manual sync when issue resolved

2. **Corrupted Index**
   - Stop scheduler
   - Restore from backup manager
   - Resume scheduler

3. **Full Rebuild**
   - Disable scheduler
   - Delete existing index files
   - Run manual sync
   - Re-enable scheduler

## Security Considerations

1. **Access Control**
   - Scheduler endpoints should be protected
   - Implement authentication for production
   - Restrict manual sync capability

2. **Data Protection**
   - Automatic backups before updates
   - Encrypted SFDC credentials
   - Secure storage of sync state

3. **Audit Trail**
   - All sync operations logged
   - History maintained for review
   - Performance metrics tracked

## Future Enhancements

1. **Update Existing Cases**
   - Currently only adds new cases
   - Future: Update modified cases
   - Requires case ID tracking

2. **Selective Sync**
   - Filter by case status
   - Filter by date ranges
   - Custom SOQL queries

3. **Advanced Scheduling**
   - Cron expression support
   - Multiple schedule rules
   - Conditional execution

4. **Notifications**
   - Email alerts on failure
   - Webhook integration
   - Slack notifications

## API Reference

See API documentation for detailed endpoint specifications:
- Scheduler endpoints: `/scheduler/*`
- Sync endpoints: `/sync/*`
- Health monitoring: `/health/*`