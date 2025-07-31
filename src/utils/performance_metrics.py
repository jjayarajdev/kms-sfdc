"""Performance metrics collection for KMS-SFDC Vector Database."""

import time
import json
from datetime import datetime
from typing import Dict, List, Optional, Callable
from pathlib import Path
from functools import wraps
from collections import defaultdict
import statistics
from loguru import logger

from .config import config


class PerformanceMetrics:
    """Collects and manages performance metrics for the system."""
    
    def __init__(self, metrics_file: str = "data/performance_metrics.json"):
        """
        Initialize performance metrics collector.
        
        Args:
            metrics_file: Path to store metrics
        """
        self.metrics_file = Path(metrics_file)
        self.metrics_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Current session metrics
        self.operation_times = defaultdict(list)
        self.operation_counts = defaultdict(int)
        self.operation_errors = defaultdict(int)
        
        # Batch processing metrics
        self.batch_metrics = []
        
        # Load historical metrics
        self.historical_metrics = self._load_metrics()
    
    def measure_time(self, operation_name: str):
        """
        Decorator to measure operation execution time.
        
        Args:
            operation_name: Name of the operation to measure
            
        Returns:
            Decorated function
        """
        def decorator(func: Callable):
            @wraps(func)
            def wrapper(*args, **kwargs):
                start_time = time.time()
                error_occurred = False
                
                try:
                    result = func(*args, **kwargs)
                    return result
                except Exception as e:
                    error_occurred = True
                    raise
                finally:
                    end_time = time.time()
                    duration_ms = (end_time - start_time) * 1000
                    
                    # Record metrics
                    self.record_operation(operation_name, duration_ms, error_occurred)
            
            return wrapper
        return decorator
    
    def record_operation(self, operation_name: str, duration_ms: float, 
                        error: bool = False, metadata: Dict = None):
        """
        Record metrics for an operation.
        
        Args:
            operation_name: Name of the operation
            duration_ms: Duration in milliseconds
            error: Whether an error occurred
            metadata: Additional metadata to store
        """
        self.operation_times[operation_name].append(duration_ms)
        self.operation_counts[operation_name] += 1
        
        if error:
            self.operation_errors[operation_name] += 1
        
        # Keep only last 1000 measurements per operation
        if len(self.operation_times[operation_name]) > 1000:
            self.operation_times[operation_name] = self.operation_times[operation_name][-1000:]
        
        # Log slow operations
        threshold_ms = 1000  # 1 second
        if duration_ms > threshold_ms:
            logger.warning(f"Slow operation '{operation_name}': {duration_ms:.0f}ms")
    
    def record_batch_processing(self, batch_size: int, processing_time_ms: float,
                               records_processed: int, operation: str = "batch"):
        """
        Record batch processing metrics.
        
        Args:
            batch_size: Size of the batch
            processing_time_ms: Total processing time
            records_processed: Number of records successfully processed
            operation: Type of batch operation
        """
        throughput = records_processed / (processing_time_ms / 1000) if processing_time_ms > 0 else 0
        
        metric = {
            "timestamp": datetime.now().isoformat(),
            "operation": operation,
            "batch_size": batch_size,
            "records_processed": records_processed,
            "processing_time_ms": processing_time_ms,
            "throughput_per_sec": throughput,
            "success_rate": records_processed / batch_size if batch_size > 0 else 0
        }
        
        self.batch_metrics.append(metric)
        
        # Log batch performance
        logger.info(f"Batch {operation}: {records_processed}/{batch_size} records "
                   f"in {processing_time_ms:.0f}ms ({throughput:.1f} records/sec)")
    
    def get_operation_stats(self, operation_name: str = None) -> Dict:
        """
        Get statistics for operations.
        
        Args:
            operation_name: Specific operation or None for all
            
        Returns:
            Statistics dictionary
        """
        if operation_name:
            return self._calculate_stats_for_operation(operation_name)
        
        # Return stats for all operations
        all_stats = {}
        for op_name in self.operation_counts.keys():
            all_stats[op_name] = self._calculate_stats_for_operation(op_name)
        
        return all_stats
    
    def _calculate_stats_for_operation(self, operation_name: str) -> Dict:
        """Calculate statistics for a specific operation."""
        times = self.operation_times.get(operation_name, [])
        count = self.operation_counts.get(operation_name, 0)
        errors = self.operation_errors.get(operation_name, 0)
        
        if not times:
            return {
                "count": 0,
                "errors": 0,
                "error_rate": 0
            }
        
        stats = {
            "count": count,
            "errors": errors,
            "error_rate": errors / count if count > 0 else 0,
            "avg_time_ms": statistics.mean(times),
            "min_time_ms": min(times),
            "max_time_ms": max(times),
            "median_time_ms": statistics.median(times),
            "std_dev_ms": statistics.stdev(times) if len(times) > 1 else 0
        }
        
        # Calculate percentiles
        if len(times) >= 10:
            sorted_times = sorted(times)
            stats["p95_time_ms"] = sorted_times[int(len(sorted_times) * 0.95)]
            stats["p99_time_ms"] = sorted_times[int(len(sorted_times) * 0.99)]
        
        return stats
    
    def get_batch_processing_summary(self) -> Dict:
        """Get summary of batch processing performance."""
        if not self.batch_metrics:
            return {"message": "No batch processing metrics available"}
        
        # Group by operation type
        by_operation = defaultdict(list)
        for metric in self.batch_metrics:
            by_operation[metric["operation"]].append(metric)
        
        summary = {}
        for operation, metrics in by_operation.items():
            throughputs = [m["throughput_per_sec"] for m in metrics]
            success_rates = [m["success_rate"] for m in metrics]
            
            summary[operation] = {
                "batch_count": len(metrics),
                "total_records": sum(m["records_processed"] for m in metrics),
                "avg_throughput_per_sec": statistics.mean(throughputs),
                "max_throughput_per_sec": max(throughputs),
                "avg_success_rate": statistics.mean(success_rates),
                "latest_batch": metrics[-1] if metrics else None
            }
        
        return summary
    
    def get_performance_report(self) -> Dict:
        """Generate comprehensive performance report."""
        report = {
            "timestamp": datetime.now().isoformat(),
            "operation_stats": self.get_operation_stats(),
            "batch_processing": self.get_batch_processing_summary(),
            "system_performance": self._get_system_performance_indicators()
        }
        
        return report
    
    def _get_system_performance_indicators(self) -> Dict:
        """Calculate system-wide performance indicators."""
        indicators = {
            "total_operations": sum(self.operation_counts.values()),
            "total_errors": sum(self.operation_errors.values()),
            "overall_error_rate": 0,
            "operations_per_type": dict(self.operation_counts)
        }
        
        if indicators["total_operations"] > 0:
            indicators["overall_error_rate"] = indicators["total_errors"] / indicators["total_operations"]
        
        # Calculate average response time across all operations
        all_times = []
        for times in self.operation_times.values():
            all_times.extend(times)
        
        if all_times:
            indicators["avg_response_time_ms"] = statistics.mean(all_times)
            indicators["median_response_time_ms"] = statistics.median(all_times)
        
        return indicators
    
    def save_metrics(self):
        """Save current metrics to disk."""
        try:
            current_metrics = {
                "timestamp": datetime.now().isoformat(),
                "operation_stats": self.get_operation_stats(),
                "batch_metrics": self.batch_metrics[-100:],  # Keep last 100 batch metrics
                "summary": self.get_performance_report()
            }
            
            # Append to historical metrics
            self.historical_metrics.append(current_metrics)
            
            # Keep only last 7 days of metrics (assuming hourly saves)
            max_entries = 7 * 24
            if len(self.historical_metrics) > max_entries:
                self.historical_metrics = self.historical_metrics[-max_entries:]
            
            # Save to file
            with open(self.metrics_file, 'w') as f:
                json.dump(self.historical_metrics, f, indent=2)
                
            logger.info("Performance metrics saved")
            
        except Exception as e:
            logger.error(f"Failed to save metrics: {e}")
    
    def _load_metrics(self) -> List[Dict]:
        """Load historical metrics from disk."""
        if self.metrics_file.exists():
            try:
                with open(self.metrics_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load metrics: {e}")
        
        return []
    
    def reset_session_metrics(self):
        """Reset current session metrics."""
        self.operation_times.clear()
        self.operation_counts.clear()
        self.operation_errors.clear()
        self.batch_metrics.clear()
        logger.info("Session metrics reset")
    
    def get_optimization_recommendations(self) -> List[Dict]:
        """Generate performance optimization recommendations."""
        recommendations = []
        
        # Check for slow operations
        for op_name, stats in self.get_operation_stats().items():
            if stats.get("count", 0) > 0:
                avg_time = stats.get("avg_time_ms", 0)
                
                if avg_time > 1000:  # > 1 second
                    recommendations.append({
                        "type": "slow_operation",
                        "operation": op_name,
                        "message": f"Operation '{op_name}' averaging {avg_time:.0f}ms - consider optimization",
                        "severity": "high" if avg_time > 5000 else "medium"
                    })
                
                error_rate = stats.get("error_rate", 0)
                if error_rate > 0.05:  # > 5% errors
                    recommendations.append({
                        "type": "high_error_rate",
                        "operation": op_name,
                        "message": f"Operation '{op_name}' has {error_rate:.1%} error rate",
                        "severity": "high"
                    })
        
        # Check batch processing
        batch_summary = self.get_batch_processing_summary()
        for op_type, summary in batch_summary.items():
            if isinstance(summary, dict) and "avg_throughput_per_sec" in summary:
                throughput = summary["avg_throughput_per_sec"]
                
                if throughput < 100:  # Less than 100 records/sec
                    recommendations.append({
                        "type": "low_throughput",
                        "operation": f"batch_{op_type}",
                        "message": f"Batch {op_type} throughput is {throughput:.1f} records/sec - consider larger batches",
                        "severity": "medium"
                    })
        
        return recommendations


# Global metrics instance
metrics_collector = PerformanceMetrics()


def track_performance(operation_name: str):
    """Decorator to track performance of functions."""
    return metrics_collector.measure_time(operation_name)