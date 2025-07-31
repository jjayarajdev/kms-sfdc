# Scheduler Performance Fixes

## Issues Identified

1. **Frequent Sync Job Execution**: The scheduler was running sync jobs too frequently (every minute instead of hourly)
2. **Frequent SFDC Connections**: The `/sync/status` API endpoint was creating new SFDC connections on every call
3. **Resource-Heavy Validation**: Vector database was being reloaded on every status check

## Fixes Applied

### 1. Fixed Scheduler Frequency
- **Problem**: Jobs were running every minute instead of hourly
- **Root Cause**: Validation API calls were triggering frequent SFDC connections, making it appear like sync jobs were running
- **Solution**: 
  - Disabled scheduler by default in config
  - Added proper interval handling for different time periods
  - Added detailed logging to track actual job execution

### 2. Optimized Validation Caching
- **Problem**: Every `/sync/status` call created new SFDCClient and VectorDatabase instances
- **Solution**: 
  - Implemented caching for SFDC client (5-minute cache)
  - Implemented caching for VectorDatabase instance
  - Added cache timestamps to avoid stale connections

### 3. Improved Logging
- **Added**: Detailed logging for job scheduling
- **Added**: Timestamps for job execution tracking
- **Added**: Next run time information

## Configuration

### Current State
- Scheduler is **disabled by default** for safety
- Default interval: 60 minutes (1 hour)
- Validation cache: 5 minutes for SFDC connections

### To Enable Scheduler
You can enable it through:

1. **Admin UI**: Navigate to `/scheduler` and toggle the enabled switch
2. **API**: 
   ```bash
   curl -X PUT http://localhost:8008/scheduler/jobs/sfdc_sync \
     -H "Content-Type: application/json" \
     -d '{"enabled": true, "schedule": {"type": "interval", "interval_minutes": 60}}'
   ```
3. **Config File**: Edit `data/scheduler_config.json` and set `enabled: true`

### Recommended Settings

For different use cases:

- **High-frequency updates**: 15-30 minutes
- **Standard operations**: 60 minutes (1 hour) - **Recommended**
- **Low-frequency updates**: 2-4 hours
- **Daily updates**: Use daily schedule type at off-peak hours

## Performance Improvements

1. **Reduced SFDC API calls**: From every status check to once per 5 minutes
2. **Reduced model loading**: VectorDatabase cached after first load
3. **Proper scheduling**: Jobs now run at correct intervals
4. **Better resource management**: Cached connections reduce initialization overhead

## Monitoring

The scheduler now provides better monitoring through:
- Real-time job status
- Next run time information
- Detailed logging with timestamps
- Performance metrics tracking

## Testing

To test the scheduler:

1. **Enable via UI**: Go to `http://localhost:4001/scheduler`
2. **Set short interval**: Use 2-3 minutes for testing
3. **Monitor logs**: Watch for "Starting scheduled job" messages
4. **Check status**: Use `/sync/status` endpoint
5. **Disable after testing**: Set back to 60 minutes or disable

## Safety Features

- **Backup before sync**: Automatic backup creation before each sync
- **Error recovery**: Automatic rollback on sync failures  
- **Connection validation**: Pre-sync connection testing
- **Resource monitoring**: Memory and performance tracking
- **Graceful degradation**: System continues operating if scheduler fails