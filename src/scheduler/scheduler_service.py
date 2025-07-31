"""Scheduler service for managing and executing cron jobs."""

import json
import os
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable
from loguru import logger
from pathlib import Path
import schedule

from src.utils.config import config


class SchedulerService:
    """Service for managing scheduled jobs with configurable cron expressions."""
    
    def __init__(self, config_file: str = "data/scheduler_config.json"):
        """Initialize the scheduler service.
        
        Args:
            config_file: Path to the scheduler configuration file
        """
        self.config_file = config_file
        self.jobs: Dict[str, schedule.Job] = {}
        self.running = False
        self.thread = None
        self.job_handlers: Dict[str, Callable] = {}
        self.job_status: Dict[str, Dict] = {}
        
        # Ensure config directory exists
        Path(self.config_file).parent.mkdir(parents=True, exist_ok=True)
        
        # Load configuration
        self.load_config()
        
    def load_config(self) -> Dict:
        """Load scheduler configuration from file."""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading scheduler config: {e}")
                return self._default_config()
        else:
            return self._default_config()
    
    def _default_config(self) -> Dict:
        """Return default scheduler configuration."""
        return {
            "jobs": [
                {
                    "id": "sfdc_sync",
                    "name": "SFDC Data Sync",
                    "description": "Synchronize new and updated cases from Salesforce",
                    "enabled": True,
                    "schedule": {
                        "type": "interval",
                        "interval_minutes": 60,
                        "start_time": "00:00"
                    },
                    "last_run": None,
                    "next_run": None,
                    "status": "idle"
                }
            ],
            "timezone": "UTC",
            "max_retries": 3,
            "retry_delay_seconds": 300
        }
    
    def save_config(self, config: Dict) -> None:
        """Save scheduler configuration to file."""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2, default=str)
            logger.info("Scheduler configuration saved successfully")
        except Exception as e:
            logger.error(f"Error saving scheduler config: {e}")
            raise
    
    def register_job_handler(self, job_id: str, handler: Callable) -> None:
        """Register a handler function for a job.
        
        Args:
            job_id: Unique identifier for the job
            handler: Function to execute when the job runs
        """
        self.job_handlers[job_id] = handler
        logger.info(f"Registered handler for job: {job_id}")
    
    def update_job_schedule(self, job_id: str, schedule_config: Dict) -> None:
        """Update the schedule for a specific job.
        
        Args:
            job_id: Job identifier
            schedule_config: New schedule configuration
        """
        config = self.load_config()
        
        # Find and update the job
        for job in config["jobs"]:
            if job["id"] == job_id:
                job["schedule"] = schedule_config
                job["next_run"] = None  # Reset next run calculation
                break
        
        # Save updated config
        self.save_config(config)
        
        # Restart scheduler if running
        if self.running:
            self.stop()
            self.start()
        
        logger.info(f"Updated schedule for job {job_id}: {schedule_config}")
    
    def enable_job(self, job_id: str, enabled: bool) -> None:
        """Enable or disable a job.
        
        Args:
            job_id: Job identifier
            enabled: Whether to enable the job
        """
        config = self.load_config()
        
        for job in config["jobs"]:
            if job["id"] == job_id:
                job["enabled"] = enabled
                break
        
        self.save_config(config)
        
        if self.running:
            self.stop()
            self.start()
        
        logger.info(f"Job {job_id} {'enabled' if enabled else 'disabled'}")
    
    def get_job_status(self, job_id: str) -> Dict:
        """Get the current status of a job.
        
        Args:
            job_id: Job identifier
            
        Returns:
            Job status information
        """
        config = self.load_config()
        
        for job in config["jobs"]:
            if job["id"] == job_id:
                # Enhance with runtime status
                status = job.copy()
                if job_id in self.job_status:
                    status.update(self.job_status[job_id])
                return status
        
        return None
    
    def get_all_jobs(self) -> List[Dict]:
        """Get status of all jobs.
        
        Returns:
            List of all job configurations with status
        """
        config = self.load_config()
        jobs = []
        
        for job in config["jobs"]:
            status = job.copy()
            if job["id"] in self.job_status:
                status.update(self.job_status[job["id"]])
            jobs.append(status)
        
        return jobs
    
    def _setup_jobs(self) -> None:
        """Set up scheduled jobs based on configuration."""
        config = self.load_config()
        
        # Clear existing jobs
        schedule.clear()
        self.jobs.clear()
        
        for job_config in config["jobs"]:
            if not job_config["enabled"]:
                continue
            
            job_id = job_config["id"]
            schedule_config = job_config["schedule"]
            
            # Create job based on schedule type
            if schedule_config["type"] == "interval":
                interval_minutes = schedule_config["interval_minutes"]
                logger.info(f"Setting up interval job {job_id} with {interval_minutes} minutes")
                
                if interval_minutes == 60:
                    # Special case for hourly
                    job = schedule.every().hour.do(self._run_job, job_id)
                    logger.info(f"Job {job_id} scheduled to run every hour")
                elif interval_minutes >= 60:
                    # For intervals >= 60 minutes, use hours
                    hours = interval_minutes / 60
                    job = schedule.every(int(hours)).hours.do(self._run_job, job_id)
                    logger.info(f"Job {job_id} scheduled to run every {int(hours)} hours")
                else:
                    # For intervals < 60 minutes, use minutes
                    job = schedule.every(interval_minutes).minutes.do(self._run_job, job_id)
                    logger.info(f"Job {job_id} scheduled to run every {interval_minutes} minutes")
                    
            elif schedule_config["type"] == "daily":
                time_str = schedule_config["time"]
                job = schedule.every().day.at(time_str).do(
                    self._run_job, job_id
                )
                logger.info(f"Job {job_id} scheduled to run daily at {time_str}")
                
            elif schedule_config["type"] == "cron":
                # For cron expressions, we'll use a different approach
                cron_expr = schedule_config["expression"]
                # This would require additional cron parsing logic
                logger.warning(f"Cron expressions not yet implemented for job {job_id}")
                continue
            
            self.jobs[job_id] = job
            logger.info(f"Job {job_id} next run time: {job.next_run}")
    
    def _run_job(self, job_id: str) -> None:
        """Execute a scheduled job.
        
        Args:
            job_id: Job identifier
        """
        logger.info(f"Starting scheduled job: {job_id} at {datetime.utcnow()}")
        
        # Update job status
        self.job_status[job_id] = {
            "status": "running",
            "start_time": datetime.utcnow().isoformat(),
            "pid": os.getpid()
        }
        
        # Update config with last run time
        config = self.load_config()
        for job in config["jobs"]:
            if job["id"] == job_id:
                job["last_run"] = datetime.utcnow().isoformat()
                job["status"] = "running"
                break
        self.save_config(config)
        
        try:
            # Execute the job handler
            if job_id in self.job_handlers:
                result = self.job_handlers[job_id]()
                
                # Update status on success
                self.job_status[job_id].update({
                    "status": "completed",
                    "end_time": datetime.utcnow().isoformat(),
                    "result": result
                })
                
                # Update config
                for job in config["jobs"]:
                    if job["id"] == job_id:
                        job["status"] = "completed"
                        job["last_success"] = datetime.utcnow().isoformat()
                        break
            else:
                logger.error(f"No handler registered for job: {job_id}")
                self.job_status[job_id]["status"] = "error"
                self.job_status[job_id]["error"] = "No handler registered"
                
        except Exception as e:
            logger.error(f"Error running job {job_id}: {e}")
            self.job_status[job_id].update({
                "status": "error",
                "end_time": datetime.utcnow().isoformat(),
                "error": str(e)
            })
            
            # Update config
            for job in config["jobs"]:
                if job["id"] == job_id:
                    job["status"] = "error"
                    job["last_error"] = str(e)
                    break
        
        finally:
            self.save_config(config)
            logger.info(f"Completed job: {job_id}")
    
    def _scheduler_loop(self) -> None:
        """Main scheduler loop."""
        while self.running:
            try:
                schedule.run_pending()
                time.sleep(1)
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                time.sleep(5)  # Wait before retrying
    
    def start(self) -> None:
        """Start the scheduler service."""
        if self.running:
            logger.warning("Scheduler is already running")
            return
        
        logger.info("Starting scheduler service")
        self.running = True
        
        # Set up jobs
        self._setup_jobs()
        
        # Start scheduler thread
        self.thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self.thread.start()
        
        logger.info("Scheduler service started")
    
    def stop(self) -> None:
        """Stop the scheduler service."""
        if not self.running:
            logger.warning("Scheduler is not running")
            return
        
        logger.info("Stopping scheduler service")
        self.running = False
        
        # Wait for thread to finish
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=5)
        
        # Clear jobs
        schedule.clear()
        self.jobs.clear()
        
        logger.info("Scheduler service stopped")
    
    def trigger_job(self, job_id: str) -> None:
        """Manually trigger a job execution.
        
        Args:
            job_id: Job identifier
        """
        logger.info(f"Manually triggering job: {job_id}")
        
        # Run in a separate thread to avoid blocking
        thread = threading.Thread(
            target=self._run_job,
            args=(job_id,),
            daemon=True
        )
        thread.start()
    
    def get_next_run_times(self) -> Dict[str, Optional[datetime]]:
        """Get next run times for all jobs.
        
        Returns:
            Dictionary mapping job IDs to their next run times
        """
        next_runs = {}
        
        for job_id, job in self.jobs.items():
            if job.next_run:
                next_runs[job_id] = job.next_run
            else:
                next_runs[job_id] = None
        
        return next_runs


# Global scheduler instance
scheduler_service = SchedulerService()