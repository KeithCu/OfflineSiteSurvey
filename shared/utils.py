"""Shared utility functions for Site Survey application.

This module contains utility functions used across both backend and frontend
components of the Site Survey application.
"""

import hashlib
import json
import logging
from PIL import Image
import io

logger = logging.getLogger(__name__)


def compute_photo_hash(image_data, algo='sha256'):
    """Compute cryptographic hash of image data for integrity verification.

    Used to ensure photo data integrity during sync and storage operations.

    Args:
        image_data (bytes): Raw image data bytes to hash
        algo (str, optional): Hash algorithm to use. Defaults to 'sha256'

    Returns:
        str or None: Hexadecimal hash string if successful, None for invalid input

    Examples:
        >>> data = b"test image data"
        >>> hash_value = compute_photo_hash(data)
        >>> len(hash_value)
        64
    """
    if isinstance(image_data, bytes):
        try:
            return hashlib.new(algo, image_data).hexdigest()
        except Exception as e:
            logger.error(f"Failed to compute photo hash with algorithm '{algo}': {e}")
            return None
    
    logger.warning(f"compute_photo_hash called with invalid input type: {type(image_data).__name__}, expected bytes")
    return None


def build_response_lookup(responses):
    """Build a response lookup dictionary for O(1) access by question_id.
    
    Pre-compute this once when a survey starts and reuse it across multiple
    conditional logic evaluations. Update it incrementally as responses are added.
    
    Args:
        responses (list): List of response dictionaries with 'question_id' and 'answer' keys
        
    Returns:
        dict: Dictionary mapping question_id -> answer value
    """
    response_lookup = {}
    for r in responses:
        qid = r.get('question_id')
        if qid is not None:
            response_lookup[qid] = r.get('answer')
    return response_lookup


def should_show_field(conditions, response_lookup):
    """Evaluate conditional logic to determine if a survey field should be displayed.

    Supports AND/OR logic with various comparison operators for building
    dynamic survey forms based on previous responses.

    Requires a pre-computed response_lookup dictionary for optimal performance.
    Always pre-compute the lookup using build_response_lookup() before calling this function.

    Args:
        conditions (dict): Condition specification with 'conditions' list and 'logic' key
            Format: {
                'conditions': [
                    {'question_id': str, 'operator': str, 'value': any}
                ],
                'logic': 'AND' | 'OR'
            }
        response_lookup (dict): Pre-computed lookup dictionary from build_response_lookup().
            Must be provided - always pre-compute this before calling.

    Returns:
        bool: True if field should be shown, False otherwise

    Supported operators:
        - 'equals': Exact string match
        - 'not_equals': String inequality
        - 'in': Value in list
        - 'not_in': Value not in list

    Examples:
        >>> conditions = {
        ...     'conditions': [{'question_id': 'q1', 'operator': 'equals', 'value': 'yes'}],
        ...     'logic': 'AND'
        ... }
        >>> responses = [{'question_id': 'q1', 'answer': 'yes'}]
        >>> lookup = build_response_lookup(responses)
        >>> should_show_field(conditions, lookup)
        True
    """
    if not conditions:
        return True

    condition_list = conditions.get('conditions', [])
    if not condition_list:
        return True

    logic = conditions.get('logic', 'AND')

    # response_lookup is required - must be pre-computed before calling
    # Default to empty dict if None (shouldn't happen in production, but safe fallback)
    if response_lookup is None:
        response_lookup = {}

    results = []
    for condition in condition_list:
        question_id = condition['question_id']
        operator = condition['operator']
        expected_value = condition['value']

        # O(1) lookup instead of O(n) linear search
        actual_value = response_lookup.get(question_id)
        if actual_value is None:
            results.append(False)
            continue

        # Convert to strings once per comparison
        actual_str = str(actual_value)
        expected_str = str(expected_value)

        if operator == 'equals':
            results.append(actual_str == expected_str)
        elif operator == 'not_equals':
            results.append(actual_str != expected_str)
        elif operator == 'in':
            # Pre-convert expected_value list once if it's a list
            if isinstance(expected_value, list):
                expected_strs = tuple(str(v) for v in expected_value)
                results.append(actual_str in expected_strs)
            else:
                results.append(actual_str == expected_str)
        elif operator == 'not_in':
            if isinstance(expected_value, list):
                expected_strs = tuple(str(v) for v in expected_value)
                results.append(actual_str not in expected_strs)
            else:
                results.append(actual_str != expected_str)

    return all(results) if logic == 'AND' else any(results)


def generate_thumbnail(image_data=None, image_path=None, max_size=200):
    """Generate a thumbnail from image data or file path while maintaining aspect ratio.

    Creates a smaller JPEG version of the image for efficient display in galleries
    and lists. Used during photo upload to create cached thumbnails.

    Args:
        image_data (bytes, optional): Raw image data bytes
        image_path (str, optional): Path to image file on disk
        max_size (int, optional): Maximum dimension for thumbnail. Defaults to 200

    Returns:
        bytes or None: JPEG thumbnail data if successful, None if generation fails

    Note:
        Thumbnails are saved with 85% JPEG quality for reasonable size/performance balance.
        PIL Image.Resampling.LANCZOS is used for high-quality downsampling.
        Either image_data or image_path must be provided.
    """
    if not image_data and not image_path:
        logger.warning("generate_thumbnail called without image_data or image_path")
        return None

    try:
        if image_path:
            img = Image.open(image_path)
        else:
            img = Image.open(io.BytesIO(image_data))

        # Calculate thumbnail size maintaining aspect ratio
        img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)

        # Save thumbnail to bytes
        thumb_buffer = io.BytesIO()
        img.save(thumb_buffer, format='JPEG', quality=85)
        return thumb_buffer.getvalue()
    except Exception as e:
        # Log error with details for debugging photo integrity issues
        if image_path:
            logger.error(f"Failed to generate thumbnail from file '{image_path}': {e}", exc_info=True)
        else:
            logger.error(f"Failed to generate thumbnail from image data (size: {len(image_data) if image_data else 0} bytes): {e}", exc_info=True)
        return None
