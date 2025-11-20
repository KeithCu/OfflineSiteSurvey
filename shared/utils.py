"""Shared utility functions for Site Survey application.

This module contains utility functions used across both backend and frontend
components of the Site Survey application.
"""

import hashlib
import json
import logging
from functools import lru_cache
from PIL import Image, UnidentifiedImageError
import io

logger = logging.getLogger(__name__)


class CorruptedImageError(Exception):
    """Raised when image data is corrupted and cannot be processed."""
    pass

# Photo hash algorithm constant - always SHA256
PHOTO_HASH_ALGO = 'sha256'


def compute_photo_hash(image_data):
    """Compute cryptographic hash of image data for integrity verification.

    Used to ensure photo data integrity during sync and storage operations.
    Always uses SHA256 algorithm.

    Args:
        image_data (bytes): Raw image data bytes to hash

    Returns:
        str: Hexadecimal hash string (64 characters for SHA256)

    Raises:
        TypeError: If image_data is not bytes type
        ValueError: If hash algorithm is invalid or unsupported

    Examples:
        >>> data = b"test image data"
        >>> hash_value = compute_photo_hash(data)
        >>> len(hash_value)
        64
    """
    if not isinstance(image_data, bytes):
        raise TypeError(f"compute_photo_hash expected bytes, got {type(image_data).__name__}")
    
    try:
        return hashlib.new(PHOTO_HASH_ALGO, image_data).hexdigest()
    except ValueError as e:
        logger.error(f"Failed to compute photo hash with algorithm '{PHOTO_HASH_ALGO}': {e}")
        raise ValueError(f"Invalid hash algorithm '{PHOTO_HASH_ALGO}': {e}") from e
    except Exception as e:
        logger.error(f"Unexpected error computing photo hash: {e}")
        raise


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

    Edge Cases:
        - Missing responses: If a question_id is not in response_lookup, the condition
          evaluates to False (conservative approach - hide field until dependency is answered)
        - None values: Explicit None values are treated as missing (False)
        - Empty strings: Empty strings are handled explicitly:
          * For 'equals'/'in': Empty string never equals non-empty value (False)
          * For 'not_equals'/'not_in': Empty string is not equal to any non-empty value (True)
        - OR logic: If any condition is True, field shows (even if others are missing)
        - AND logic: All conditions must be True (missing responses cause False)

    Examples:
        >>> conditions = {
        ...     'conditions': [{'question_id': 'q1', 'operator': 'equals', 'value': 'yes'}],
        ...     'logic': 'AND'
        ... }
        >>> responses = [{'question_id': 'q1', 'answer': 'yes'}]
        >>> lookup = build_response_lookup(responses)
        >>> should_show_field(conditions, lookup)
        True
        
        >>> # Missing response - field hidden
        >>> should_show_field(conditions, {})
        False
        
        >>> # OR logic with one missing - still evaluates correctly
        >>> conditions_or = {
        ...     'conditions': [
        ...         {'question_id': 'q1', 'operator': 'equals', 'value': 'yes'},
        ...         {'question_id': 'q2', 'operator': 'equals', 'value': 'yes'}
        ...     ],
        ...     'logic': 'OR'
        ... }
        >>> lookup = {'q2': 'yes'}  # q1 missing, q2 matches
        >>> should_show_field(conditions_or, lookup)
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
        # Check if question_id exists in lookup (distinguishes missing vs None value)
        if question_id not in response_lookup:
            # Response not provided yet - conservative approach: hide field until answered
            # This prevents fields from showing erroneously when dependencies aren't met
            results.append(False)
            continue

        actual_value = response_lookup[question_id]
        
        # Handle explicit None or empty string values
        # None means no answer provided, empty string means explicitly empty answer
        if actual_value is None:
            # Explicit None value - treat as missing for all operators
            results.append(False)
            continue

        # Convert to strings once per comparison
        actual_str = str(actual_value)
        expected_str = str(expected_value)

        # Handle empty string explicitly for better edge case handling
        if actual_str == '' and operator in ('equals', 'in'):
            # Empty string never equals non-empty value
            results.append(False)
            continue
        elif actual_str == '' and operator in ('not_equals', 'not_in'):
            # Empty string is not equal to any non-empty value
            results.append(True)
            continue

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
        else:
            # Unknown operator - conservative approach: hide field
            logger.warning(f"Unknown operator '{operator}' in conditional logic for question_id '{question_id}'")
            results.append(False)

    return all(results) if logic == 'AND' else any(results)


@lru_cache(maxsize=128)
def _calculate_thumbnail_size(original_width, original_height, max_size):
    """Calculate thumbnail dimensions maintaining aspect ratio.
    
    Cached to avoid recalculating dimensions for the same inputs.
    This is useful when generating multiple thumbnails with the same
    max_size from images with the same dimensions.
    
    Args:
        original_width (int): Original image width
        original_height (int): Original image height
        max_size (int): Maximum dimension for thumbnail
        
    Returns:
        tuple: (width, height) tuple for thumbnail dimensions
    """
    if original_width <= max_size and original_height <= max_size:
        return (original_width, original_height)
    
    # Calculate scaling factor to fit within max_size while maintaining aspect ratio
    ratio = min(max_size / original_width, max_size / original_height)
    new_width = int(original_width * ratio)
    new_height = int(original_height * ratio)
    
    return (new_width, new_height)


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
            (for non-corruption errors like missing files)

    Raises:
        CorruptedImageError: When image data is corrupted and cannot be processed.
            Callers should catch this and flag the photo as corrupted in the database.

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
    
    except UnidentifiedImageError as e:
        # Image file is corrupted or in unsupported format
        error_msg = f"Corrupted or unsupported image format"
        if image_path:
            logger.error(f"{error_msg} - file '{image_path}': {e}", exc_info=True)
            raise CorruptedImageError(f"Image file '{image_path}' is corrupted or in unsupported format: {e}") from e
        else:
            logger.error(f"{error_msg} - image data (size: {len(image_data) if image_data else 0} bytes): {e}", exc_info=True)
            raise CorruptedImageError(f"Image data is corrupted or in unsupported format: {e}") from e
    
    except OSError as e:
        # File system errors that may indicate corruption (e.g., "cannot identify image file")
        if "cannot identify image file" in str(e).lower() or "truncated" in str(e).lower():
            error_msg = f"Corrupted image file"
            if image_path:
                logger.error(f"{error_msg} '{image_path}': {e}", exc_info=True)
                raise CorruptedImageError(f"Image file '{image_path}' is corrupted: {e}") from e
            else:
                logger.error(f"{error_msg} - image data (size: {len(image_data) if image_data else 0} bytes): {e}", exc_info=True)
                raise CorruptedImageError(f"Image data is corrupted: {e}") from e
        else:
            # Other OSError (file not found, permission denied, etc.) - return None
            if image_path:
                logger.warning(f"OSError reading image file '{image_path}': {e}")
            else:
                logger.warning(f"OSError processing image data: {e}")
            return None
    
    except (IOError, ValueError) as e:
        # IOError/ValueError during image processing may indicate corruption
        error_msg = f"Error processing image"
        if image_path:
            logger.error(f"{error_msg} '{image_path}': {e}", exc_info=True)
            raise CorruptedImageError(f"Image file '{image_path}' cannot be processed: {e}") from e
        else:
            logger.error(f"{error_msg} - image data (size: {len(image_data) if image_data else 0} bytes): {e}", exc_info=True)
            raise CorruptedImageError(f"Image data cannot be processed: {e}") from e
    
    except Exception as e:
        # Unexpected errors - log but don't assume corruption
        if image_path:
            logger.error(f"Unexpected error generating thumbnail from file '{image_path}': {e}", exc_info=True)
        else:
            logger.error(f"Unexpected error generating thumbnail from image data (size: {len(image_data) if image_data else 0} bytes): {e}", exc_info=True)
        return None
