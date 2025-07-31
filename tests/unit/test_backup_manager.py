"""
Unit tests for backup manager functionality.
"""

import pytest
import os
import json
import shutil
import tempfile
from unittest.mock import Mock, patch, mock_open
from datetime import datetime

from src.utils.backup_manager import BackupManager


@pytest.mark.unit
class TestBackupManager:
    """Test cases for BackupManager class."""

    def test_init(self, temp_dir):
        """Test BackupManager initialization."""
        backup_manager = BackupManager(backup_dir=temp_dir)
        
        assert backup_manager.backup_dir == temp_dir
        assert backup_manager.max_backups == 10  # Default value
        assert os.path.exists(backup_manager.metadata_file)

    def test_init_creates_backup_directory(self, temp_dir):
        """Test that backup directory is created if it doesn't exist."""
        backup_dir = os.path.join(temp_dir, 'new_backup_dir')
        backup_manager = BackupManager(backup_dir=backup_dir)
        
        assert os.path.exists(backup_dir)
        assert backup_manager.backup_dir == backup_dir

    def test_generate_backup_id(self, temp_dir):
        """Test backup ID generation."""
        backup_manager = BackupManager(backup_dir=temp_dir)
        
        backup_id = backup_manager._generate_backup_id()
        
        # Should be in format YYYYMMDD_HHMMSS
        assert len(backup_id) == 15
        assert '_' in backup_id
        
        # Should be parseable as datetime
        datetime.strptime(backup_id, "%Y%m%d_%H%M%S")

    def test_create_backup_success(self, temp_dir):
        """Test successful backup creation."""
        backup_manager = BackupManager(backup_dir=temp_dir)
        
        # Create test files to backup
        index_file = os.path.join(temp_dir, 'test_index.bin')
        metadata_file = os.path.join(temp_dir, 'test_metadata.json')
        
        with open(index_file, 'w') as f:
            f.write('test index data')
        with open(metadata_file, 'w') as f:
            json.dump({'test': 'metadata'}, f)
        
        backup_id = backup_manager.create_backup(
            index_path=index_file,
            metadata_path=metadata_file,
            description="Test backup"
        )
        
        assert backup_id is not None
        
        # Check backup directory was created
        backup_path = os.path.join(temp_dir, backup_id)
        assert os.path.exists(backup_path)
        
        # Check files were copied
        assert os.path.exists(os.path.join(backup_path, 'faiss_index.bin'))
        assert os.path.exists(os.path.join(backup_path, 'case_metadata.json'))
        assert os.path.exists(os.path.join(backup_path, 'backup_info.json'))

    def test_create_backup_missing_source_files(self, temp_dir):
        """Test backup creation with missing source files."""
        backup_manager = BackupManager(backup_dir=temp_dir)
        
        nonexistent_index = os.path.join(temp_dir, 'nonexistent_index.bin')
        nonexistent_metadata = os.path.join(temp_dir, 'nonexistent_metadata.json')
        
        with pytest.raises(FileNotFoundError):
            backup_manager.create_backup(
                index_path=nonexistent_index,
                metadata_path=nonexistent_metadata
            )

    def test_create_backup_info_file(self, temp_dir):
        """Test that backup info file is created correctly."""
        backup_manager = BackupManager(backup_dir=temp_dir)
        
        # Create test files
        index_file = os.path.join(temp_dir, 'test_index.bin')
        metadata_file = os.path.join(temp_dir, 'test_metadata.json')
        
        with open(index_file, 'w') as f:
            f.write('test data')
        with open(metadata_file, 'w') as f:
            json.dump({'test': 'data'}, f)
        
        backup_id = backup_manager.create_backup(
            index_path=index_file,
            metadata_path=metadata_file,
            description="Test backup with description"
        )
        
        # Check backup info file
        backup_info_path = os.path.join(temp_dir, backup_id, 'backup_info.json')
        assert os.path.exists(backup_info_path)
        
        with open(backup_info_path, 'r') as f:
            backup_info = json.load(f)
        
        assert backup_info['backup_id'] == backup_id
        assert backup_info['description'] == "Test backup with description"
        assert 'timestamp' in backup_info
        assert 'files' in backup_info
        assert len(backup_info['files']) == 2

    def test_list_backups_empty(self, temp_dir):
        """Test listing backups when none exist."""
        backup_manager = BackupManager(backup_dir=temp_dir)
        
        backups = backup_manager.list_backups()
        
        assert backups == []

    def test_list_backups_with_data(self, temp_dir):
        """Test listing backups with existing backup data."""
        backup_manager = BackupManager(backup_dir=temp_dir)
        
        # Create a mock backup directory and info file
        backup_id = "20240101_120000"
        backup_path = os.path.join(temp_dir, backup_id)
        os.makedirs(backup_path)
        
        backup_info = {
            'backup_id': backup_id,
            'timestamp': '2024-01-01T12:00:00',
            'description': 'Test backup',
            'files': ['index.bin', 'metadata.json']
        }
        
        with open(os.path.join(backup_path, 'backup_info.json'), 'w') as f:
            json.dump(backup_info, f)
        
        backups = backup_manager.list_backups()
        
        assert len(backups) == 1
        assert backups[0]['backup_id'] == backup_id
        assert backups[0]['description'] == 'Test backup'

    def test_get_backup_info_success(self, temp_dir):
        """Test getting backup info for existing backup."""
        backup_manager = BackupManager(backup_dir=temp_dir)
        
        # Create mock backup
        backup_id = "20240101_120000"
        backup_path = os.path.join(temp_dir, backup_id)
        os.makedirs(backup_path)
        
        backup_info = {
            'backup_id': backup_id,
            'timestamp': '2024-01-01T12:00:00',
            'description': 'Test backup'
        }
        
        with open(os.path.join(backup_path, 'backup_info.json'), 'w') as f:
            json.dump(backup_info, f)
        
        info = backup_manager.get_backup_info(backup_id)
        
        assert info['backup_id'] == backup_id
        assert info['description'] == 'Test backup'

    def test_get_backup_info_not_found(self, temp_dir):
        """Test getting backup info for non-existent backup."""
        backup_manager = BackupManager(backup_dir=temp_dir)
        
        info = backup_manager.get_backup_info('nonexistent_backup')
        
        assert info is None

    def test_restore_backup_success(self, temp_dir):
        """Test successful backup restoration."""
        backup_manager = BackupManager(backup_dir=temp_dir)
        
        # Create a backup first
        index_file = os.path.join(temp_dir, 'original_index.bin')
        metadata_file = os.path.join(temp_dir, 'original_metadata.json')
        
        with open(index_file, 'w') as f:
            f.write('original index data')
        with open(metadata_file, 'w') as f:
            json.dump({'original': 'metadata'}, f)
        
        backup_id = backup_manager.create_backup(index_file, metadata_file)
        
        # Now restore it to different locations
        restore_index = os.path.join(temp_dir, 'restored_index.bin')
        restore_metadata = os.path.join(temp_dir, 'restored_metadata.json')
        
        success = backup_manager.restore_backup(
            backup_id=backup_id,
            index_path=restore_index,
            metadata_path=restore_metadata
        )
        
        assert success is True
        assert os.path.exists(restore_index)
        assert os.path.exists(restore_metadata)
        
        # Check content was restored correctly
        with open(restore_index, 'r') as f:
            assert f.read() == 'original index data'

    def test_restore_backup_not_found(self, temp_dir):
        """Test restoring non-existent backup."""
        backup_manager = BackupManager(backup_dir=temp_dir)
        
        success = backup_manager.restore_backup(
            backup_id='nonexistent',
            index_path='restore_index.bin',
            metadata_path='restore_metadata.json'
        )
        
        assert success is False

    def test_delete_backup_success(self, temp_dir):
        """Test successful backup deletion."""
        backup_manager = BackupManager(backup_dir=temp_dir)
        
        # Create a backup first
        backup_id = "20240101_120000"
        backup_path = os.path.join(temp_dir, backup_id)
        os.makedirs(backup_path)
        
        # Create some files in backup
        with open(os.path.join(backup_path, 'test_file.txt'), 'w') as f:
            f.write('test')
        
        # Create backup info
        backup_info = {'backup_id': backup_id}
        with open(os.path.join(backup_path, 'backup_info.json'), 'w') as f:
            json.dump(backup_info, f)
        
        success = backup_manager.delete_backup(backup_id)
        
        assert success is True
        assert not os.path.exists(backup_path)

    def test_delete_backup_not_found(self, temp_dir):
        """Test deleting non-existent backup."""
        backup_manager = BackupManager(backup_dir=temp_dir)
        
        success = backup_manager.delete_backup('nonexistent')
        
        assert success is False

    def test_cleanup_old_backups(self, temp_dir):
        """Test cleanup of old backups beyond max limit."""
        backup_manager = BackupManager(backup_dir=temp_dir, max_backups=2)
        
        # Create 3 mock backups
        backup_ids = ["20240101_120000", "20240102_120000", "20240103_120000"]
        
        for backup_id in backup_ids:
            backup_path = os.path.join(temp_dir, backup_id)
            os.makedirs(backup_path)
            
            backup_info = {
                'backup_id': backup_id,
                'timestamp': f'2024-01-{backup_id[6:8]}T12:00:00'
            }
            
            with open(os.path.join(backup_path, 'backup_info.json'), 'w') as f:
                json.dump(backup_info, f)
        
        # Trigger cleanup
        backup_manager._cleanup_old_backups()
        
        # Should only have 2 most recent backups
        remaining_backups = backup_manager.list_backups()
        assert len(remaining_backups) == 2
        
        # Should have kept the 2 most recent
        remaining_ids = [b['backup_id'] for b in remaining_backups]
        assert "20240102_120000" in remaining_ids
        assert "20240103_120000" in remaining_ids
        assert "20240101_120000" not in remaining_ids

    def test_get_backup_size(self, temp_dir):
        """Test calculating backup size."""
        backup_manager = BackupManager(backup_dir=temp_dir)
        
        # Create test files with known sizes
        index_file = os.path.join(temp_dir, 'test_index.bin')
        metadata_file = os.path.join(temp_dir, 'test_metadata.json')
        
        with open(index_file, 'w') as f:
            f.write('x' * 1000)  # 1000 bytes
        with open(metadata_file, 'w') as f:
            f.write('y' * 500)   # 500 bytes
        
        backup_id = backup_manager.create_backup(index_file, metadata_file)
        
        size = backup_manager.get_backup_size(backup_id)
        
        # Should be approximately 1500 bytes plus backup_info.json
        assert size > 1500
        assert size < 2000  # Account for backup_info.json

    def test_get_backup_size_not_found(self, temp_dir):
        """Test getting size of non-existent backup."""
        backup_manager = BackupManager(backup_dir=temp_dir)
        
        size = backup_manager.get_backup_size('nonexistent')
        
        assert size == 0

    def test_validate_backup_integrity(self, temp_dir):
        """Test backup integrity validation."""
        backup_manager = BackupManager(backup_dir=temp_dir)
        
        # Create a complete backup
        index_file = os.path.join(temp_dir, 'test_index.bin')
        metadata_file = os.path.join(temp_dir, 'test_metadata.json')
        
        with open(index_file, 'w') as f:
            f.write('test index')
        with open(metadata_file, 'w') as f:
            json.dump({'test': 'metadata'}, f)
        
        backup_id = backup_manager.create_backup(index_file, metadata_file)
        
        is_valid = backup_manager.validate_backup_integrity(backup_id)
        
        assert is_valid is True

    def test_validate_backup_integrity_corrupted(self, temp_dir):
        """Test validation of corrupted backup."""
        backup_manager = BackupManager(backup_dir=temp_dir)
        
        # Create backup directory manually (simulating corruption)
        backup_id = "20240101_120000"
        backup_path = os.path.join(temp_dir, backup_id)
        os.makedirs(backup_path)
        
        # Only create backup_info.json, missing actual files
        backup_info = {
            'backup_id': backup_id,
            'files': ['faiss_index.bin', 'case_metadata.json']
        }
        
        with open(os.path.join(backup_path, 'backup_info.json'), 'w') as f:
            json.dump(backup_info, f)
        
        is_valid = backup_manager.validate_backup_integrity(backup_id)
        
        assert is_valid is False

    def test_backup_metadata_update(self, temp_dir):
        """Test that backup metadata is properly updated."""
        backup_manager = BackupManager(backup_dir=temp_dir)
        
        # Initially should be empty
        assert backup_manager._load_backup_metadata() == {}
        
        # Create a backup
        index_file = os.path.join(temp_dir, 'test_index.bin')
        metadata_file = os.path.join(temp_dir, 'test_metadata.json')
        
        with open(index_file, 'w') as f:
            f.write('test')
        with open(metadata_file, 'w') as f:
            json.dump({}, f)
        
        backup_id = backup_manager.create_backup(index_file, metadata_file)
        
        # Metadata should be updated
        metadata = backup_manager._load_backup_metadata()
        assert backup_id in metadata
        assert metadata[backup_id]['status'] == 'completed'

    def test_concurrent_backup_creation(self, temp_dir):
        """Test that concurrent backup creation is handled safely."""
        import threading
        
        backup_manager = BackupManager(backup_dir=temp_dir)
        
        # Create test files
        index_file = os.path.join(temp_dir, 'test_index.bin')
        metadata_file = os.path.join(temp_dir, 'test_metadata.json')
        
        with open(index_file, 'w') as f:
            f.write('test index')
        with open(metadata_file, 'w') as f:
            json.dump({'test': 'metadata'}, f)
        
        backup_ids = []
        
        def create_backup():
            backup_id = backup_manager.create_backup(index_file, metadata_file)
            backup_ids.append(backup_id)
        
        # Create multiple backups concurrently
        threads = [threading.Thread(target=create_backup) for _ in range(3)]
        
        for thread in threads:
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # All backups should have been created successfully
        assert len(backup_ids) == 3
        assert len(set(backup_ids)) == 3  # All should be unique
        
        # All backups should exist
        for backup_id in backup_ids:
            assert backup_id is not None
            backup_path = os.path.join(temp_dir, backup_id)
            assert os.path.exists(backup_path)

    def test_backup_compression(self, temp_dir):
        """Test backup compression functionality if implemented."""
        backup_manager = BackupManager(backup_dir=temp_dir)
        
        # Create large test files
        index_file = os.path.join(temp_dir, 'large_index.bin')
        metadata_file = os.path.join(temp_dir, 'large_metadata.json')
        
        with open(index_file, 'w') as f:
            f.write('x' * 10000)  # 10KB file
        with open(metadata_file, 'w') as f:
            json.dump({'data': 'y' * 5000}, f)  # ~5KB file
        
        backup_id = backup_manager.create_backup(
            index_file, 
            metadata_file,
            compress=False  # Test without compression first
        )
        
        # Backup should exist and contain the files
        backup_path = os.path.join(temp_dir, backup_id)
        assert os.path.exists(backup_path)
        
        # Files should be copied (not compressed in this basic test)
        backup_index = os.path.join(backup_path, 'faiss_index.bin')
        assert os.path.exists(backup_index)
        assert os.path.getsize(backup_index) == 10000