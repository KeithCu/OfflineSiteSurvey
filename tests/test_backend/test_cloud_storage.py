"""Tests for cloud storage service."""

import pytest
import os
from unittest.mock import Mock, patch, MagicMock
from backend.services.cloud_storage import CloudStorageService


@pytest.fixture
def mock_env():
    """Set up mock environment variables."""
    env_vars = {
        'CLOUD_STORAGE_PROVIDER': 's3',
        'CLOUD_STORAGE_ACCESS_KEY': 'test_key',
        'CLOUD_STORAGE_SECRET_KEY': 'test_secret',
        'CLOUD_STORAGE_BUCKET': 'test-bucket',
        'CLOUD_STORAGE_REGION': 'us-east-1',
        'CLOUD_STORAGE_LOCAL_PATH': './test_local_photos'
    }
    with patch.dict(os.environ, env_vars):
        yield env_vars


@pytest.fixture
def mock_driver():
    """Create a mock libcloud driver."""
    driver = Mock()
    container = Mock()
    container.name = 'test-bucket'
    driver.get_container.return_value = container
    driver.list_containers.return_value = [container]

    # Mock object for upload/download
    obj = Mock()
    obj.get_cdn_url.return_value = 'https://cdn.example.com/test.jpg'
    obj.public_url = 'https://example.com/test.jpg'
    driver.upload_object_via_stream.return_value = obj
    driver.get_object.return_value = obj

    return driver


@patch('backend.services.cloud_storage.get_driver')
def test_cloud_storage_initialization(mock_get_driver, mock_env, mock_driver):
    """Test cloud storage service initialization."""
    mock_get_driver.return_value = mock_driver

    service = CloudStorageService()

    assert service.provider_name == 's3'
    assert service.bucket_name == 'test-bucket'
    mock_get_driver.assert_called_once()
    assert service.driver is not None


@patch('backend.services.cloud_storage.get_driver')
def test_upload_photo_success(mock_get_driver, mock_env, tmp_path):
    """Test successful photo upload."""
    mock_driver = Mock()
    container = Mock()
    container.name = 'test-bucket'
    mock_driver.get_container.return_value = container

    # Mock successful upload
    uploaded_obj = Mock()
    uploaded_obj.configure_mock(**{
        'get_cdn_url.return_value': 'https://cdn.example.com/photos/test.jpg',
        'public_url': 'https://example.com/photos/test.jpg'
    })
    mock_driver.upload_object_via_stream.return_value = uploaded_obj

    mock_get_driver.return_value = mock_driver

    service = CloudStorageService()

    # Create test file
    test_file = tmp_path / "test.jpg"
    test_file.write_bytes(b'test_image_data')

    result = service.upload_photo(
        photo_id='test-photo-id',
        photo_path=str(test_file),
        site_id=1
    )

    assert result['photo_url'] == 'https://cloud-storage.example.com/1/test-photo-id.jpg'
    assert result['object_name'] == '1/test-photo-id.jpg'
    assert result['thumbnail_url'] is None  # No thumbnail provided


