"""Tests for backend utility functions."""
import pytest
from shared.utils import compute_photo_hash, should_show_field, generate_thumbnail, build_response_lookup


def test_compute_photo_hash():
    """Test photo hash computation."""
    # Test with valid bytes
    test_data = b"test image data"
    hash_value = compute_photo_hash(test_data)
    assert hash_value is not None
    assert len(hash_value) == 64  # SHA-256 hex length
    assert isinstance(hash_value, str)

    # Test with None/invalid input
    assert compute_photo_hash(None) is None
    assert compute_photo_hash("not bytes") is None


def test_should_show_field():
    """Test conditional field logic."""
    # Test with no conditions (should always show)
    assert should_show_field(None, {}) is True
    assert should_show_field({}, {}) is True

    # Test AND logic with single condition
    conditions = {
        'conditions': [{
            'question_id': 'q1',
            'operator': 'equals',
            'value': 'yes'
        }],
        'logic': 'AND'
    }
    responses = [{'question_id': 'q1', 'answer': 'yes'}]
    lookup = build_response_lookup(responses)
    assert should_show_field(conditions, lookup) is True

    responses = [{'question_id': 'q1', 'answer': 'no'}]
    lookup = build_response_lookup(responses)
    assert should_show_field(conditions, lookup) is False

    # Test OR logic with multiple conditions
    conditions = {
        'conditions': [
            {'question_id': 'q1', 'operator': 'equals', 'value': 'yes'},
            {'question_id': 'q2', 'operator': 'equals', 'value': 'yes'}
        ],
        'logic': 'OR'
    }
    responses = [{'question_id': 'q1', 'answer': 'yes'}, {'question_id': 'q2', 'answer': 'no'}]
    lookup = build_response_lookup(responses)
    assert should_show_field(conditions, lookup) is True

    responses = [{'question_id': 'q1', 'answer': 'no'}, {'question_id': 'q2', 'answer': 'no'}]
    lookup = build_response_lookup(responses)
    assert should_show_field(conditions, lookup) is False

    # Test different operators
    conditions = {
        'conditions': [{'question_id': 'q1', 'operator': 'not_equals', 'value': 'yes'}],
        'logic': 'AND'
    }
    responses = [{'question_id': 'q1', 'answer': 'no'}]
    lookup = build_response_lookup(responses)
    assert should_show_field(conditions, lookup) is True

    # Test 'in' operator
    conditions = {
        'conditions': [{'question_id': 'q1', 'operator': 'in', 'value': ['a', 'b', 'c']}],
        'logic': 'AND'
    }
    responses = [{'question_id': 'q1', 'answer': 'b'}]
    lookup = build_response_lookup(responses)
    assert should_show_field(conditions, lookup) is True

    responses = [{'question_id': 'q1', 'answer': 'd'}]
    lookup = build_response_lookup(responses)
    assert should_show_field(conditions, lookup) is False


def test_generate_thumbnail():
    """Test thumbnail generation."""
    # Create a simple test image
    from PIL import Image
    import io

    # Create a test image
    test_image = Image.new('RGB', (100, 100), color='red')
    img_buffer = io.BytesIO()
    test_image.save(img_buffer, format='JPEG')
    image_data = img_buffer.getvalue()

    # Test thumbnail generation
    thumbnail = generate_thumbnail(image_data, max_size=50)
    assert thumbnail is not None
    assert isinstance(thumbnail, bytes)

    # Verify thumbnail is smaller
    assert len(thumbnail) < len(image_data)

    # Test with None input
    assert generate_thumbnail(None) is None

    # Test with empty data
    assert generate_thumbnail(b"") is None
