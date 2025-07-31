"""FastAPI-based search API for KMS-SFDC Vector Database."""

from typing import List, Optional, Dict
from datetime import datetime
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from loguru import logger

from ..utils.config import config
from ..vectorization import VectorDatabase
from ..utils.health_monitor import HealthMonitor
from ..utils.performance_metrics import metrics_collector
from ..scheduler import scheduler_service, sfdc_sync_job


class SearchRequest(BaseModel):
    """Request model for similarity search."""
    query: str = Field(..., min_length=1, max_length=1000, description="Search query text")
    top_k: Optional[int] = Field(None, ge=1, le=100, description="Number of results to return")
    similarity_threshold: Optional[float] = Field(None, ge=0.0, le=1.0, description="Minimum similarity score")


class CaseResult(BaseModel):
    """Model for case search result."""
    similarity_score: float
    case_id: str
    case_number: str
    subject_description: str
    description_description: str
    issue_plain_text: str
    cause_plain_text: str
    resolution_plain_text: str
    status_text: str
    textbody: str
    created_date: str
    preview_text: str


class SearchResponse(BaseModel):
    """Response model for similarity search."""
    query: str
    results: List[CaseResult]
    total_results: int
    search_time_ms: float


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str
    vector_db_ready: bool
    total_vectors: int
    model_name: str


class ScheduleConfig(BaseModel):
    """Schedule configuration model."""
    type: str = Field(..., description="Schedule type: interval, daily, or cron")
    interval_minutes: Optional[int] = Field(None, ge=1, le=1440, description="Interval in minutes (for interval type)")
    time: Optional[str] = Field(None, description="Time of day (HH:MM format for daily type)")
    expression: Optional[str] = Field(None, description="Cron expression (for cron type)")


class JobScheduleUpdate(BaseModel):
    """Request model for updating job schedule."""
    enabled: bool = Field(..., description="Whether the job is enabled")
    schedule: ScheduleConfig = Field(..., description="Schedule configuration")


class SyncJobStatus(BaseModel):
    """Sync job status response."""
    id: str
    name: str
    description: str
    enabled: bool
    schedule: Dict
    last_run: Optional[str] = None
    next_run: Optional[str] = None
    status: str
    last_success: Optional[str] = None
    last_error: Optional[str] = None


class ManualSyncRequest(BaseModel):
    """Request model for manual sync."""
    start_date: Optional[str] = Field(None, description="Start date for sync (YYYY-MM-DD)")
    end_date: Optional[str] = Field(None, description="End date for sync (YYYY-MM-DD)")


# Initialize FastAPI app
app = FastAPI(
    title=config.api.title,
    version=config.api.version,
    description="Vector-based similarity search API for HPE SFDC case data"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize vector database
vector_db = VectorDatabase()

# Initialize health monitor
health_monitor = HealthMonitor()

# Try to load existing index on startup
try:
    vector_db.load_index()
    logger.info("Vector database loaded successfully")
except FileNotFoundError:
    logger.warning("No existing vector database found. Index needs to be built.")
except Exception as e:
    logger.error(f"Error loading vector database: {e}")


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    logger.info("KMS-SFDC Vector Search API starting up")
    # Start health monitoring
    health_monitor.start_monitoring(interval=60)  # Check every minute
    
    # Register sync job handler
    scheduler_service.register_job_handler("sfdc_sync", sfdc_sync_job.run)
    
    # Start scheduler service
    scheduler_service.start()
    logger.info("Scheduler service started")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("KMS-SFDC Vector Search API shutting down")
    # Stop health monitoring
    health_monitor.stop_monitoring()
    # Stop scheduler
    scheduler_service.stop()


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    stats = vector_db.get_stats()
    
    return HealthResponse(
        status="healthy",
        vector_db_ready=stats["is_trained"],
        total_vectors=stats["total_vectors"],
        model_name=stats["model_name"]
    )


@app.post("/search", response_model=SearchResponse)
async def search_similar_cases(request: SearchRequest):
    """
    Search for similar cases using vector similarity.
    
    Args:
        request: Search parameters including query text
        
    Returns:
        List of similar cases with similarity scores
    """
    import time
    start_time = time.time()
    
    if not vector_db.is_trained:
        raise HTTPException(
            status_code=503,
            detail="Vector database not ready. Index needs to be built."
        )
    
    try:
        # Perform similarity search
        results = vector_db.search(
            query_text=request.query,
            top_k=request.top_k,
            similarity_threshold=request.similarity_threshold
        )
        
        # Convert to response format
        case_results = [CaseResult(**result) for result in results]
        
        search_time = (time.time() - start_time) * 1000  # Convert to milliseconds
        
        # Record request metrics
        health_monitor.record_request(search_time, error=False)
        
        logger.info(f"Search completed in {search_time:.2f}ms, found {len(case_results)} results")
        
        return SearchResponse(
            query=request.query,
            results=case_results,
            total_results=len(case_results),
            search_time_ms=round(search_time, 2)
        )
        
    except Exception as e:
        logger.error(f"Error during search: {e}")
        # Record error
        health_monitor.record_request(0, error=True)
        raise HTTPException(status_code=500, detail=f"Search error: {str(e)}")


@app.get("/search")
async def search_similar_cases_get(
    q: str = Query(..., description="Search query text"),
    top_k: Optional[int] = Query(None, ge=1, le=100, description="Number of results"),
    threshold: Optional[float] = Query(None, ge=0.0, le=1.0, description="Similarity threshold")
):
    """
    GET endpoint for similarity search (for simple URL-based queries).
    """
    request = SearchRequest(
        query=q,
        top_k=top_k,
        similarity_threshold=threshold
    )
    return await search_similar_cases(request)


@app.get("/stats")
async def get_database_stats():
    """Get vector database statistics."""
    return vector_db.get_stats()


@app.get("/health/detailed")
async def detailed_health_check():
    """Get detailed health check with system metrics."""
    return health_monitor.check_health()


@app.get("/health/report")
async def health_report(hours: int = Query(24, description="Hours to include in report")):
    """Get health report for specified time period."""
    return health_monitor.get_health_report(hours=hours)


@app.get("/health/metrics")
async def get_metrics_summary():
    """Get current metrics summary."""
    return health_monitor.get_metrics_summary()


@app.get("/performance/report")
async def get_performance_report():
    """Get comprehensive performance report."""
    return metrics_collector.get_performance_report()


@app.get("/performance/operations")
async def get_operation_stats(operation: str = Query(None, description="Specific operation name")):
    """Get performance statistics for operations."""
    return metrics_collector.get_operation_stats(operation)


@app.get("/performance/batch")
async def get_batch_performance():
    """Get batch processing performance summary."""
    return metrics_collector.get_batch_processing_summary()


@app.get("/performance/recommendations")
async def get_performance_recommendations():
    """Get performance optimization recommendations."""
    return metrics_collector.get_optimization_recommendations()


@app.post("/performance/save")
async def save_performance_metrics():
    """Save current performance metrics to disk."""
    metrics_collector.save_metrics()
    return {"status": "saved", "timestamp": datetime.now().isoformat()}


@app.post("/rebuild-index")
async def rebuild_index():
    """
    Trigger index rebuild (admin endpoint).
    
    Note: This should be protected with authentication in production.
    """
    try:
        # This endpoint would typically trigger a background job
        # For now, return status indicating rebuild is needed
        return {
            "message": "Index rebuild triggered",
            "status": "started",
            "note": "This operation runs in background. Check /health for completion status."
        }
    except Exception as e:
        logger.error(f"Error triggering index rebuild: {e}")
        raise HTTPException(status_code=500, detail=f"Rebuild error: {str(e)}")


# Scheduler endpoints
@app.get("/scheduler/jobs", response_model=List[SyncJobStatus])
async def get_scheduler_jobs():
    """Get all scheduled jobs."""
    return scheduler_service.get_all_jobs()


@app.get("/scheduler/jobs/{job_id}", response_model=SyncJobStatus)
async def get_job_status(job_id: str):
    """Get status of a specific job."""
    status = scheduler_service.get_job_status(job_id)
    if not status:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    return status


@app.put("/scheduler/jobs/{job_id}")
async def update_job_schedule(job_id: str, update: JobScheduleUpdate):
    """Update job schedule configuration."""
    try:
        # Update enabled state
        scheduler_service.enable_job(job_id, update.enabled)
        
        # Update schedule if enabled
        if update.enabled:
            scheduler_service.update_job_schedule(job_id, update.schedule.dict())
        
        return {"status": "updated", "job_id": job_id}
    except Exception as e:
        logger.error(f"Error updating job schedule: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/scheduler/jobs/{job_id}/trigger")
async def trigger_job(job_id: str):
    """Manually trigger a job execution."""
    try:
        scheduler_service.trigger_job(job_id)
        return {"status": "triggered", "job_id": job_id}
    except Exception as e:
        logger.error(f"Error triggering job: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/sync/status")
async def get_sync_status():
    """Get current synchronization status and statistics."""
    try:
        stats = sfdc_sync_job.get_sync_stats()
        validation = sfdc_sync_job.validate_sync()
        
        return {
            "stats": stats,
            "validation": validation,
            "scheduler_running": scheduler_service.running
        }
    except Exception as e:
        logger.error(f"Error getting sync status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/sync/manual")
async def manual_sync(request: Optional[ManualSyncRequest] = None):
    """Trigger a manual synchronization."""
    try:
        # For manual sync, we'll trigger the job directly
        # In a production system, this might queue the job instead
        logger.info("Manual sync requested")
        
        # Trigger the sync job
        scheduler_service.trigger_job("sfdc_sync")
        
        return {
            "status": "triggered",
            "message": "Manual sync has been triggered. Check /sync/status for progress."
        }
    except Exception as e:
        logger.error(f"Error triggering manual sync: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/sync/history")
async def get_sync_history(limit: int = Query(10, ge=1, le=100)):
    """Get synchronization history."""
    try:
        state = sfdc_sync_job.load_state()
        history = state.get("sync_history", [])
        
        # Return most recent entries
        return {
            "history": history[-limit:],
            "total_syncs": len(history),
            "total_cases_synced": state.get("total_cases_synced", 0)
        }
    except Exception as e:
        logger.error(f"Error getting sync history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}")
    return HTTPException(status_code=500, detail="Internal server error")


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "src.search.api:app",
        host=config.api.host,
        port=config.api.port,
        reload=True,
        log_level="info"
    )