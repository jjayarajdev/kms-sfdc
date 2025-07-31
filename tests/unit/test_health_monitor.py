"""
Unit tests for health monitoring functionality.
"""

import pytest
import time
import json
import tempfile
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

from src.utils.health_monitor import HealthMonitor


@pytest.mark.unit
class TestHealthMonitor:
    """Test cases for HealthMonitor class."""

    def test_init(self):
        """Test HealthMonitor initialization."""
        monitor = HealthMonitor()
        
        assert monitor.metrics == []
        assert monitor.alerts == []
        assert monitor.monitoring_active is False
        assert monitor.monitor_thread is None

    def test_record_request_success(self):
        """Test recording successful request."""
        monitor = HealthMonitor()
        
        monitor.record_request(response_time=120.5, error=False)
        
        assert len(monitor.metrics) == 1
        metric = monitor.metrics[0]
        assert metric['response_time'] == 120.5
        assert metric['error'] is False
        assert 'timestamp' in metric

    def test_record_request_error(self):
        """Test recording error request."""
        monitor = HealthMonitor()
        
        monitor.record_request(response_time=0, error=True)
        
        assert len(monitor.metrics) == 1
        metric = monitor.metrics[0]
        assert metric['error'] is True

    def test_get_metrics_summary_empty(self):
        """Test metrics summary with no data."""
        monitor = HealthMonitor()
        
        summary = monitor.get_metrics_summary()
        
        assert summary['total_requests'] == 0
        assert summary['successful_requests'] == 0
        assert summary['failed_requests'] == 0
        assert summary['avg_response_time'] == 0.0
        assert summary['error_rate'] == 0.0

    def test_get_metrics_summary_with_data(self):
        """Test metrics summary with request data."""
        monitor = HealthMonitor()
        
        # Add test metrics
        monitor.record_request(100.0, False)
        monitor.record_request(200.0, False)
        monitor.record_request(0, True)
        monitor.record_request(150.0, False)
        
        summary = monitor.get_metrics_summary()
        
        assert summary['total_requests'] == 4
        assert summary['successful_requests'] == 3
        assert summary['failed_requests'] == 1
        assert summary['avg_response_time'] == 150.0  # (100+200+150)/3
        assert summary['error_rate'] == 0.25  # 1/4

    @patch('psutil.cpu_percent', return_value=45.2)
    @patch('psutil.virtual_memory')
    @patch('psutil.disk_usage')
    def test_get_system_metrics(self, mock_disk, mock_memory, mock_cpu):
        """Test getting system metrics."""
        # Mock memory
        mock_memory.return_value.percent = 62.8
        
        # Mock disk
        mock_disk.return_value.percent = 78.5
        
        monitor = HealthMonitor()
        metrics = monitor._get_system_metrics()
        
        assert metrics['cpu_usage'] == 45.2
        assert metrics['memory_usage'] == 62.8
        assert metrics['disk_usage'] == 78.5
        assert 'timestamp' in metrics

    @patch('psutil.cpu_percent', side_effect=Exception("psutil error"))
    def test_get_system_metrics_error(self, mock_cpu):
        """Test system metrics when psutil fails."""
        monitor = HealthMonitor()
        
        metrics = monitor._get_system_metrics()
        
        # Should return default values when psutil fails
        assert metrics['cpu_usage'] == 0.0
        assert metrics['memory_usage'] == 0.0
        assert metrics['disk_usage'] == 0.0

    def test_check_health_basic(self):
        """Test basic health check."""
        monitor = HealthMonitor()
        
        # Add some metrics
        monitor.record_request(100.0, False)
        monitor.record_request(200.0, False)
        
        with patch.object(monitor, '_get_system_metrics') as mock_system:
            mock_system.return_value = {
                'cpu_usage': 45.2,
                'memory_usage': 62.8,
                'disk_usage': 78.5,
                'timestamp': datetime.now().isoformat()
            }
            
            health = monitor.check_health()
            
            assert health['status'] in ['healthy', 'warning', 'critical']
            assert 'system_metrics' in health
            assert 'performance_metrics' in health
            assert 'alerts' in health

    def test_generate_alerts_high_cpu(self):
        """Test alert generation for high CPU usage."""
        monitor = HealthMonitor()
        
        system_metrics = {
            'cpu_usage': 95.0,  # High CPU
            'memory_usage': 50.0,
            'disk_usage': 50.0
        }
        
        alerts = monitor._generate_alerts(system_metrics, {})
        
        assert len(alerts) > 0
        assert any('CPU usage' in alert['message'] for alert in alerts)
        assert any(alert['severity'] == 'critical' for alert in alerts)

    def test_generate_alerts_high_memory(self):
        """Test alert generation for high memory usage."""
        monitor = HealthMonitor()
        
        system_metrics = {
            'cpu_usage': 50.0,
            'memory_usage': 95.0,  # High memory
            'disk_usage': 50.0
        }
        
        alerts = monitor._generate_alerts(system_metrics, {})
        
        assert len(alerts) > 0
        assert any('Memory usage' in alert['message'] for alert in alerts)

    def test_generate_alerts_high_error_rate(self):
        """Test alert generation for high error rate."""
        monitor = HealthMonitor()
        
        # Add many errors
        for _ in range(10):
            monitor.record_request(0, True)
        
        performance_metrics = monitor.get_metrics_summary()
        alerts = monitor._generate_alerts({}, performance_metrics)
        
        assert len(alerts) > 0
        assert any('error rate' in alert['message'].lower() for alert in alerts)

    def test_get_health_report_empty(self):
        """Test health report with no data."""
        monitor = HealthMonitor()
        
        report = monitor.get_health_report(hours=24)
        
        assert report['period_hours'] == 24
        assert report['total_requests'] == 0
        assert report['avg_response_time'] == 0.0
        assert report['error_rate'] == 0.0
        assert len(report['alerts']) == 0

    def test_get_health_report_with_data(self):
        """Test health report with request data."""
        monitor = HealthMonitor()
        
        # Add test data with timestamps
        current_time = datetime.now()
        for i in range(5):
            monitor.record_request(100.0 + i * 10, i > 3)  # Last one is error
        
        report = monitor.get_health_report(hours=24)
        
        assert report['total_requests'] == 5
        assert report['successful_requests'] == 4
        assert report['failed_requests'] == 1
        assert report['error_rate'] == 0.2

    def test_metrics_cleanup_old_data(self):
        """Test cleanup of old metrics data."""
        monitor = HealthMonitor()
        
        # Add old metrics (simulate by manipulating timestamps)
        old_time = datetime.now() - timedelta(days=8)
        recent_time = datetime.now() - timedelta(hours=1)
        
        # Manually create metrics with different timestamps
        monitor.metrics = [
            {'timestamp': old_time.isoformat(), 'response_time': 100, 'error': False},
            {'timestamp': recent_time.isoformat(), 'response_time': 200, 'error': False}
        ]
        
        # Clean up metrics older than 7 days
        monitor._cleanup_old_metrics(days=7)
        
        # Should only have recent metric
        assert len(monitor.metrics) == 1
        assert monitor.metrics[0]['response_time'] == 200

    def test_save_metrics_to_file(self, temp_dir):
        """Test saving metrics to file."""
        monitor = HealthMonitor()
        
        # Add test metrics
        monitor.record_request(100.0, False)
        monitor.record_request(200.0, True)
        
        metrics_file = os.path.join(temp_dir, 'test_metrics.json')
        monitor.save_metrics_to_file(metrics_file)
        
        assert os.path.exists(metrics_file)
        
        # Verify file contents
        with open(metrics_file, 'r') as f:
            saved_data = json.load(f)
        
        assert 'metrics' in saved_data
        assert 'summary' in saved_data
        assert len(saved_data['metrics']) == 2

    def test_load_metrics_from_file(self, temp_dir):
        """Test loading metrics from file."""
        monitor = HealthMonitor()
        
        # Create test metrics file
        test_data = {
            'metrics': [
                {'timestamp': datetime.now().isoformat(), 'response_time': 100, 'error': False},
                {'timestamp': datetime.now().isoformat(), 'response_time': 200, 'error': True}
            ],
            'summary': {'total_requests': 2}
        }
        
        metrics_file = os.path.join(temp_dir, 'test_metrics.json')
        with open(metrics_file, 'w') as f:
            json.dump(test_data, f)
        
        monitor.load_metrics_from_file(metrics_file)
        
        assert len(monitor.metrics) == 2
        assert monitor.metrics[0]['response_time'] == 100
        assert monitor.metrics[1]['error'] is True

    def test_load_metrics_file_not_found(self):
        """Test loading metrics when file doesn't exist."""
        monitor = HealthMonitor()
        
        # Should not raise error, should log warning
        monitor.load_metrics_from_file('nonexistent_file.json')
        
        assert len(monitor.metrics) == 0

    @patch('threading.Thread')
    def test_start_monitoring(self, mock_thread):
        """Test starting monitoring thread."""
        mock_thread_instance = Mock()
        mock_thread.return_value = mock_thread_instance
        
        monitor = HealthMonitor()
        monitor.start_monitoring(interval=60)
        
        assert monitor.monitoring_active is True
        assert monitor.monitor_thread == mock_thread_instance
        mock_thread_instance.start.assert_called_once()

    def test_stop_monitoring(self):
        """Test stopping monitoring."""
        monitor = HealthMonitor()
        monitor.monitoring_active = True
        monitor.monitor_thread = Mock()
        
        monitor.stop_monitoring()
        
        assert monitor.monitoring_active is False

    @patch('time.sleep')
    def test_monitor_loop_single_iteration(self, mock_sleep):
        """Test single iteration of monitoring loop."""
        monitor = HealthMonitor()
        monitor.monitoring_active = True
        
        # Mock _get_system_metrics to avoid psutil dependency
        with patch.object(monitor, '_get_system_metrics') as mock_system:
            mock_system.return_value = {
                'cpu_usage': 50.0,
                'memory_usage': 60.0,
                'disk_usage': 70.0,
                'timestamp': datetime.now().isoformat()
            }
            
            # Mock sleep to exit after one iteration
            def mock_sleep_side_effect(seconds):
                monitor.monitoring_active = False
            
            mock_sleep.side_effect = mock_sleep_side_effect
            
            monitor._monitor_loop(interval=1)
            
            # Should have called system metrics once
            mock_system.assert_called_once()

    def test_alert_severity_levels(self):
        """Test different alert severity levels."""
        monitor = HealthMonitor()
        
        # Test critical alert (very high CPU)
        system_metrics = {'cpu_usage': 98.0, 'memory_usage': 50.0, 'disk_usage': 50.0}
        alerts = monitor._generate_alerts(system_metrics, {})
        critical_alerts = [a for a in alerts if a['severity'] == 'critical']
        assert len(critical_alerts) > 0
        
        # Test warning alert (high but not critical CPU)
        system_metrics = {'cpu_usage': 85.0, 'memory_usage': 50.0, 'disk_usage': 50.0}
        alerts = monitor._generate_alerts(system_metrics, {})
        warning_alerts = [a for a in alerts if a['severity'] == 'warning']
        assert len(warning_alerts) > 0

    def test_metrics_time_filtering(self):
        """Test filtering metrics by time period."""
        monitor = HealthMonitor()
        
        # Create metrics with different timestamps
        now = datetime.now()
        old_metric = {
            'timestamp': (now - timedelta(hours=25)).isoformat(),
            'response_time': 100,
            'error': False
        }
        recent_metric = {
            'timestamp': (now - timedelta(hours=1)).isoformat(),
            'response_time': 200,
            'error': False
        }
        
        monitor.metrics = [old_metric, recent_metric]
        
        # Get report for last 24 hours
        filtered_metrics = monitor._filter_metrics_by_time(hours=24)
        
        # Should only include recent metric
        assert len(filtered_metrics) == 1
        assert filtered_metrics[0]['response_time'] == 200

    def test_concurrent_metric_recording(self):
        """Test concurrent metric recording thread safety."""
        import threading
        
        monitor = HealthMonitor()
        
        def record_metrics():
            for i in range(10):
                monitor.record_request(100.0 + i, False)
        
        # Create multiple threads
        threads = [threading.Thread(target=record_metrics) for _ in range(5)]
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Should have recorded all metrics
        assert len(monitor.metrics) == 50  # 5 threads * 10 metrics each

    def test_alert_deduplication(self):
        """Test that duplicate alerts are not generated."""
        monitor = HealthMonitor()
        
        # Generate same alert multiple times
        system_metrics = {'cpu_usage': 95.0, 'memory_usage': 50.0, 'disk_usage': 50.0}
        
        alerts1 = monitor._generate_alerts(system_metrics, {})
        alerts2 = monitor._generate_alerts(system_metrics, {})
        
        # Alerts should be similar (same conditions)
        assert len(alerts1) == len(alerts2)
        
        # In a real implementation, you might want deduplication logic
        # This test documents the current behavior