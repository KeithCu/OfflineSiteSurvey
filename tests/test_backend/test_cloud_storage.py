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
    """Test successful photo upload with verification."""
    mock_driver = Mock()
    container = Mock()
    container.name = 'test-bucket'
    mock_driver.get_container.return_value = container

    # Mock successful upload and download
    uploaded_obj = Mock()
    uploaded_obj.get_cdn_url.return_value = 'https://cdn.example.com/photos/test.jpg'
    uploaded_obj.public_url = 'https://example.com/photos/test.jpg'
    uploaded_obj.download.return_value = b'test_image_data'
    mock_driver.upload_object_via_stream.return_value = uploaded_obj

    mock_get_driver.return_value = mock_driver

    service = CloudStorageService()

    # Create test file
    test_file = tmp_path / "test.jpg"
    test_file.write_bytes(b'test_image_data')

    result = service.upload_photo(
        photo_id='test-photo-id',
        photo_path=str(test_file),
        expected_hash='d08693b15844a2a1d15f9f8df8d18d547bfb860408d4f0486f496300ffbfbfe6',  # hash of 'test_image_data'
        site_id=1
    )

    assert result['photo_url'] == 'https://cdn.example.com/photos/test.jpg'
    assert result['object_name'] == 'photos/1/test-photo-id.jpg'
    assert 'thumbnail_url' not in result  # No thumbnail provided


@patch('backend.services.cloud_storage.get_driver')
def test_upload_photo_verification_failure(mock_get_driver, mock_env, tmp_path):
    """Test photo upload with verification failure."""
    mock_driver = Mock()
    container = Mock()
    container.name = 'test-bucket'
    mock_driver.get_container.return_value = container

    uploaded_obj = Mock()
    uploaded_obj.download.return_value = b'different_data'
    mock_driver.upload_object_via_stream.return_value = uploaded_obj

    mock_get_driver.return_value = mock_driver

    service = CloudStorageService()

    # Create test file
    test_file = tmp_path / "test.jpg"
    test_file.write_bytes(b'test_image_data')

    with pytest.raises(ValueError, match="Upload verification failed"):
        service.upload_photo(
            photo_id='test-photo-id',
            photo_path=str(test_file),
            expected_hash='d08693b15844a2a1d15f9f8df8d18d547bfb860408d4f0486f496300ffbfbfe6',  # hash of 'test_image_data'
            site_id=1
        )

    # Verify object was deleted on failure
    mock_driver.delete_object.assert_called_once_with(uploaded_obj)


@patch('backend.services.cloud_storage.get_driver')
def test_download_photo(mock_get_driver, mock_env):
    """Test photo download."""
    mock_driver = Mock()
    container = Mock()
    container.name = 'test-bucket'
    mock_driver.get_container.return_value = container

    obj = Mock()
    obj.download.return_value = b'test_image_data'
    mock_driver.get_object.return_value = obj

    mock_get_driver.return_value = mock_driver

    service = CloudStorageService()

    data = service.download_photo('photos/test.jpg')

    assert data == b'test_image_data'
    mock_driver.get_object.assert_called_once_with('test-bucket', 'photos/test.jpg')
