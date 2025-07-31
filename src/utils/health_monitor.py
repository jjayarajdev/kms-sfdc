"""Health monitoring utilities for KMS-SFDC Vector Database."""

import time
import psutil
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import json
import threading
from loguru import logger

from .config import config


class HealthMonitor:
    """Monitors health and performance of the vector database system."""
    
    def __init__(self, metrics_file: str = "data/health_metrics.json"):
        """
        Initialize health monitor.
        
        Args:
            metrics_file: Path to store metrics history
        """
        self.metrics_file = Path(metrics_file)
        self.metrics_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Health thresholds
        self.thresholds = {
            "memory_usage_percent": 80,  # Alert if memory > 80%
            "cpu_usage_percent": 90,     # Alert if CPU > 90%
            "disk_space_gb": 5,          # Alert if disk < 5GB
            "response_time_ms": 1000,    # Alert if response > 1s
            "error_rate_percent": 5      # Alert if error rate > 5%
        }
        
        # Metrics collection
        self.current_metrics = {}
        self.metrics_history = self._load_metrics_history()
        
        # Performance tracking
        self.request_times = []
        self.error_count = 0
        self.total_requests = 0
        self.start_time = time.time()
        
        # Background monitoring thread
        self.monitoring_active = False
        self.monitor_thread = None
    
    def start_monitoring(self, interval: int = 60):
        """
        Start background health monitoring.
        
        Args:
            interval: Seconds between health checks
        """
        if self.monitoring_active:
            logger.warning("Health monitoring already active")
            return
        
        self.monitoring_active = True
        self.monitor_thread = threading.Thread(
            target=self._monitor_loop,
            args=(interval,),
            daemon=True
        )
        self.monitor_thread.start()
        logger.info(f"Health monitoring started with {interval}s interval")
    
    def stop_monitoring(self):
        """Stop background health monitoring."""
        self.monitoring_active = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        logger.info("Health monitoring stopped")
    
    def check_health(self) -> Dict:
        """
        Perform comprehensive health check.
        
        Returns:
            Health status dictionary
        """
        health_status = {
            "timestamp": datetime.now().isoformat(),
            "status": "healthy",
            "checks": {},
            "alerts": []
        }
        
        # System resource checks
        health_status["checks"]["system"] = self._check_system_resources()
        
        # FAISS index health
        health_status["checks"]["index"] = self._check_index_health()
        
        # API performance
        health_status["checks"]["performance"] = self._check_performance()
        
        # Data freshness
        health_status["checks"]["data"] = self._check_data_freshness()
        
        # Check thresholds and generate alerts
        alerts = self._check_thresholds(health_status["checks"])
        health_status["alerts"] = alerts
        
        # Determine overall status
        if alerts:
            health_status["status"] = "warning" if len(alerts) < 3 else "critical"
        
        # Save current metrics
        self.current_metrics = health_status
        self._save_metrics_history(health_status)
        
        return health_status
    
    def _check_system_resources(self) -> Dict:
        """Check system resource usage."""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            
            # Disk usage
            disk = psutil.disk_usage('/')
            
            # Process-specific memory
            process = psutil.Process(os.getpid())
            process_memory = process.memory_info()
            
            return {
                "cpu_usage_percent": cpu_percent,
                "memory_usage_percent": memory.percent,
                "memory_available_gb": memory.available / (1024**3),
                "disk_free_gb": disk.free / (1024**3),
                "disk_usage_percent": disk.percent,
                "process_memory_mb": process_memory.rss / (1024**2)
            }
        except Exception as e:
            logger.error(f"System resource check failed: {e}")
            return {"error": str(e)}
    
    def _check_index_health(self) -> Dict:
        """Check FAISS index health."""
        index_health = {
            "index_exists": False,
            "metadata_exists": False,
            "index_size_mb": 0,
            "metadata_size_mb": 0,
            "last_modified": None
        }
        
        try:
            # Check index file
            index_path = Path(config.vectordb.index_path)
            if index_path.exists():
                index_health["index_exists"] = True
                index_health["index_size_mb"] = index_path.stat().st_size / (1024**2)
                index_health["last_modified"] = datetime.fromtimestamp(
                    index_path.stat().st_mtime
                ).isoformat()
            
            # Check metadata file
            metadata_path = Path(config.vectordb.metadata_path)
            if metadata_path.exists():
                index_health["metadata_exists"] = True
                index_health["metadata_size_mb"] = metadata_path.stat().st_size / (1024**2)
                
                # Try to load and check metadata integrity
                try:
                    with open(metadata_path, 'r') as f:
                        metadata = json.load(f)
                        index_health["metadata_count"] = len(metadata)
                except Exception as e:
                    index_health["metadata_error"] = str(e)
            
            # Check backup status
            backup_dir = Path("data/backups")
            if backup_dir.exists():
                backups = list(backup_dir.glob("*/backup_info.json"))
                index_health["backup_count"] = len(backups)
                if backups:
                    latest_backup = max(backups, key=lambda x: x.stat().st_mtime)
                    index_health["latest_backup"] = latest_backup.parent.name
            
        except Exception as e:
            logger.error(f"Index health check failed: {e}")
            index_health["error"] = str(e)
        
        return index_health
    
    def _check_performance(self) -> Dict:
        """Check API performance metrics."""
        performance = {
            "uptime_hours": (time.time() - self.start_time) / 3600,
            "total_requests": self.total_requests,
            "error_count": self.error_count,
            "error_rate_percent": 0
        }
        
        if self.total_requests > 0:
            performance["error_rate_percent"] = (self.error_count / self.total_requests) * 100
        
        if self.request_times:
            # Calculate response time statistics
            performance["avg_response_time_ms"] = sum(self.request_times) / len(self.request_times)
            performance["max_response_time_ms"] = max(self.request_times)
            performance["min_response_time_ms"] = min(self.request_times)
            
            # Calculate percentiles
            sorted_times = sorted(self.request_times)
            performance["p95_response_time_ms"] = sorted_times[int(len(sorted_times) * 0.95)]
            performance["p99_response_time_ms"] = sorted_times[int(len(sorted_times) * 0.99)]
        
        # Clear old request times (keep last 1000)
        if len(self.request_times) > 1000:
            self.request_times = self.request_times[-1000:]
        
        return performance
    
    def _check_data_freshness(self) -> Dict:
        """Check data freshness and update status."""
        data_status = {
            "index_age_hours": 0,
            "needs_update": False
        }
        
        try:
            index_path = Path(config.vectordb.index_path)
            if index_path.exists():
                last_modified = datetime.fromtimestamp(index_path.stat().st_mtime)
                age = datetime.now() - last_modified
                data_status["index_age_hours"] = age.total_seconds() / 3600
                
                # Consider index stale after 24 hours
                data_status["needs_update"] = data_status["index_age_hours"] > 24
                data_status["last_update"] = last_modified.isoformat()
        
        except Exception as e:
            logger.error(f"Data freshness check failed: {e}")
            data_status["error"] = str(e)
        
        return data_status
    
    def _check_thresholds(self, checks: Dict) -> List[Dict]:
        """Check metrics against thresholds and generate alerts."""
        alerts = []
        
        # System resource alerts
        if "system" in checks and "error" not in checks["system"]:
            sys = checks["system"]
            
            if sys["cpu_usage_percent"] > self.thresholds["cpu_usage_percent"]:
                alerts.append({
                    "type": "cpu_high",
                    "severity": "warning",
                    "message": f"CPU usage high: {sys['cpu_usage_percent']:.1f}%",
                    "value": sys["cpu_usage_percent"]
                })
            
            if sys["memory_usage_percent"] > self.thresholds["memory_usage_percent"]:
                alerts.append({
                    "type": "memory_high",
                    "severity": "warning",
                    "message": f"Memory usage high: {sys['memory_usage_percent']:.1f}%",
                    "value": sys["memory_usage_percent"]
                })
            
            if sys["disk_free_gb"] < self.thresholds["disk_space_gb"]:
                alerts.append({
                    "type": "disk_low",
                    "severity": "critical",
                    "message": f"Low disk space: {sys['disk_free_gb']:.1f}GB free",
                    "value": sys["disk_free_gb"]
                })
        
        # Performance alerts
        if "performance" in checks:
            perf = checks["performance"]
            
            if "avg_response_time_ms" in perf and perf["avg_response_time_ms"] > self.thresholds["response_time_ms"]:
                alerts.append({
                    "type": "slow_response",
                    "severity": "warning",
                    "message": f"Slow response times: {perf['avg_response_time_ms']:.0f}ms average",
                    "value": perf["avg_response_time_ms"]
                })
            
            if perf["error_rate_percent"] > self.thresholds["error_rate_percent"]:
                alerts.append({
                    "type": "high_errors",
                    "severity": "critical",
                    "message": f"High error rate: {perf['error_rate_percent']:.1f}%",
                    "value": perf["error_rate_percent"]
                })
        
        # Index health alerts
        if "index" in checks:
            idx = checks["index"]
            
            if not idx["index_exists"]:
                alerts.append({
                    "type": "index_missing",
                    "severity": "critical",
                    "message": "FAISS index file not found",
                    "value": None
                })
            
            if not idx["metadata_exists"]:
                alerts.append({
                    "type": "metadata_missing",
                    "severity": "critical",
                    "message": "Metadata file not found",
                    "value": None
                })
        
        return alerts
    
    def record_request(self, response_time_ms: float, error: bool = False):
        """
        Record API request metrics.
        
        Args:
            response_time_ms: Response time in milliseconds
            error: Whether the request resulted in an error
        """
        self.total_requests += 1
        if error:
            self.error_count += 1
        else:
            self.request_times.append(response_time_ms)
    
    def get_metrics_summary(self) -> Dict:
        """Get current metrics summary."""
        if not self.current_metrics:
            self.current_metrics = self.check_health()
        
        return {
            "status": self.current_metrics.get("status", "unknown"),
            "timestamp": self.current_metrics.get("timestamp", ""),
            "alerts": len(self.current_metrics.get("alerts", [])),
            "uptime_hours": self.current_metrics.get("checks", {}).get("performance", {}).get("uptime_hours", 0),
            "total_requests": self.total_requests,
            "error_rate": self.current_metrics.get("checks", {}).get("performance", {}).get("error_rate_percent", 0)
        }
    
    def _monitor_loop(self, interval: int):
        """Background monitoring loop."""
        while self.monitoring_active:
            try:
                health_status = self.check_health()
                
                # Log alerts
                for alert in health_status.get("alerts", []):
                    if alert["severity"] == "critical":
                        logger.error(f"CRITICAL: {alert['message']}")
                    else:
                        logger.warning(f"WARNING: {alert['message']}")
                
                # Sleep until next check
                time.sleep(interval)
                
            except Exception as e:
                logger.error(f"Health monitoring error: {e}")
                time.sleep(interval)
    
    def _load_metrics_history(self) -> List[Dict]:
        """Load metrics history from disk."""
        if self.metrics_file.exists():
            try:
                with open(self.metrics_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load metrics history: {e}")
        
        return []
    
    def _save_metrics_history(self, metrics: Dict):
        """Save metrics to history file."""
        try:
            # Add to history
            self.metrics_history.append(metrics)
            
            # Keep only last 24 hours of metrics (assuming 1-minute intervals)
            max_entries = 24 * 60
            if len(self.metrics_history) > max_entries:
                self.metrics_history = self.metrics_history[-max_entries:]
            
            # Save to file
            with open(self.metrics_file, 'w') as f:
                json.dump(self.metrics_history, f, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to save metrics history: {e}")
    
    def get_health_report(self, hours: int = 24) -> Dict:
        """
        Generate comprehensive health report.
        
        Args:
            hours: Number of hours to include in report
            
        Returns:
            Health report dictionary
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        # Filter metrics within time range
        recent_metrics = [
            m for m in self.metrics_history
            if datetime.fromisoformat(m["timestamp"]) > cutoff_time
        ]
        
        if not recent_metrics:
            return {"error": "No metrics available for specified time range"}
        
        # Calculate statistics
        report = {
            "time_range_hours": hours,
            "metrics_count": len(recent_metrics),
            "overall_health": self._calculate_health_score(recent_metrics),
            "alerts_summary": self._summarize_alerts(recent_metrics),
            "resource_usage": self._summarize_resources(recent_metrics),
            "performance_summary": self._summarize_performance(recent_metrics)
        }
        
        return report
    
    def _calculate_health_score(self, metrics: List[Dict]) -> float:
        """Calculate overall health score (0-100)."""
        if not metrics:
            return 0.0
        
        scores = []
        for m in metrics:
            score = 100.0
            
            # Deduct points for alerts
            alerts = m.get("alerts", [])
            for alert in alerts:
                if alert["severity"] == "critical":
                    score -= 20
                else:
                    score -= 10
            
            scores.append(max(0, score))
        
        return sum(scores) / len(scores)
    
    def _summarize_alerts(self, metrics: List[Dict]) -> Dict:
        """Summarize alerts from metrics."""
        alert_counts = {}
        
        for m in metrics:
            for alert in m.get("alerts", []):
                alert_type = alert["type"]
                alert_counts[alert_type] = alert_counts.get(alert_type, 0) + 1
        
        return alert_counts
    
    def _summarize_resources(self, metrics: List[Dict]) -> Dict:
        """Summarize resource usage from metrics."""
        cpu_values = []
        memory_values = []
        
        for m in metrics:
            sys = m.get("checks", {}).get("system", {})
            if "cpu_usage_percent" in sys:
                cpu_values.append(sys["cpu_usage_percent"])
            if "memory_usage_percent" in sys:
                memory_values.append(sys["memory_usage_percent"])
        
        summary = {}
        if cpu_values:
            summary["avg_cpu_percent"] = sum(cpu_values) / len(cpu_values)
            summary["max_cpu_percent"] = max(cpu_values)
        
        if memory_values:
            summary["avg_memory_percent"] = sum(memory_values) / len(memory_values)
            summary["max_memory_percent"] = max(memory_values)
        
        return summary
    
    def _summarize_performance(self, metrics: List[Dict]) -> Dict:
        """Summarize performance from metrics."""
        response_times = []
        error_rates = []
        
        for m in metrics:
            perf = m.get("checks", {}).get("performance", {})
            if "avg_response_time_ms" in perf:
                response_times.append(perf["avg_response_time_ms"])
            if "error_rate_percent" in perf:
                error_rates.append(perf["error_rate_percent"])
        
        summary = {}
        if response_times:
            summary["avg_response_time_ms"] = sum(response_times) / len(response_times)
            summary["max_response_time_ms"] = max(response_times)
        
        if error_rates:
            summary["avg_error_rate_percent"] = sum(error_rates) / len(error_rates)
            summary["max_error_rate_percent"] = max(error_rates)
        
        return summary