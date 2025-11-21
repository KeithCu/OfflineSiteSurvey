"""Shared utility functions for Site Survey application.

This module contains utility functions used across both backend and frontend
components of the Site Survey application.
"""

import hashlib
import json
import logging
import operator
from functools import lru_cache, wraps
from PIL import Image, UnidentifiedImageError
import io

logger = logging.getLogger(__name__)


class CorruptedImageError(Exception):
    """Raised when image data is corrupted and cannot be processed."""
    pass


def handle_image_errors(func):
    """Decorator to handle image processing errors consistently.
    
    Converts image processing exceptions to CorruptedImageError or returns None
    for non-corruption errors. Handles logging automatically.
    
    The decorated function should accept image_path and/or image_data as keyword arguments
    for proper error message formatting.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        image_path = kwargs.get('image_path')
        image_data = kwargs.get('image_data')
        
        def log_and_raise(msg, exc, is_corruption=True):
            error_source = f"file '{image_path}'" if image_path else f"image data (size: {len(image_data) if image_data else 0} bytes)"
            full_msg = f"{msg} - {error_source}: {exc}"
            logger.error(full_msg, exc_info=True)
            if is_corruption:
                raise CorruptedImageError(f"{msg}: {exc}") from exc
            return None

        try:
            return func(*args, **kwargs)
        except UnidentifiedImageError as e:
            log_and_raise("Corrupted or unsupported image format", e)
        except OSError as e:
            if "cannot identify image file" in str(e).lower() or "truncated" in str(e).lower():
                log_and_raise("Corrupted image file", e)
            else:
                if image_path:
                    logger.warning(f"OSError reading image file '{image_path}': {e}")
                else:
                    logger.warning(f"OSError processing image data: {e}")
                return None
        except (IOError, ValueError) as e:
            log_and_raise("Error processing image", e)
        except Exception as e:
            log_and_raise("Unexpected error generating thumbnail", e, is_corruption=False)
            return None
    
    return wrapper


# Photo hash algorithm constant - always SHA256
PHOTO_HASH_ALGO = 'sha256'

# Operator dispatch for conditional logic evaluation
OPERATORS = {
    'equals': operator.eq,
    'not_equals': operator.ne,
    'in': lambda x, y: str(x) in [str(v) for v in y] if isinstance(y, list) else str(x) == str(y),
    'not_in': lambda x, y: str(x) not in [str(v) for v in y] if isinstance(y, list) else str(x) != str(y),
}


def compute_photo_hash(image_data_or_path):
    """Compute cryptographic hash of image data for integrity verification.

    Used to ensure photo data integrity during sync and storage operations.
    Always uses SHA256 algorithm. Can accept bytes, file path, or file-like object.

    Args:
        image_data_or_path: Raw bytes, file path (str), or file-like object

    Returns:
        str: Hexadecimal hash string (64 characters for SHA256)

    Raises:
        TypeError: If input type is invalid
        ValueError: If hash algorithm is invalid or unsupported
        FileNotFoundError: If image_data_or_path is a path and file doesn't exist
    """
    try:
        hasher = hashlib.new(PHOTO_HASH_ALGO)

        if isinstance(image_data_or_path, str):
            # Read file in chunks to avoid loading large files into memory
            try:
                with open(image_data_or_path, 'rb') as f:
                    while chunk := f.read(8192):  # Read 8KB chunks
                        hasher.update(chunk)
            except FileNotFoundError:
                logger.error(f"Photo file not found: {image_data_or_path}")
                raise
            except Exception as e:
                logger.error(f"Error reading photo file '{image_data_or_path}': {e}")
                raise
        elif isinstance(image_data_or_path, bytes):
            # Use memoryview to avoid copying if possible, though hashlib likely copies anyway
            hasher.update(image_data_or_path)
        elif hasattr(image_data_or_path, 'read'):
            # File-like object (stream)
            while chunk := image_data_or_path.read(8192):
                hasher.update(chunk)
        else:
            raise TypeError(f"compute_photo_hash expected bytes, str (path), or file-like object, got {type(image_data_or_path).__name__}")

        return hasher.hexdigest()
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

        # Use operator dispatch for O(1) lookup instead of O(n) if/elif chain
        op_func = OPERATORS.get(operator)
        if op_func:
            results.append(op_func(actual_str, expected_value))
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


@handle_image_errors
def generate_thumbnail(image_data=None, image_path=None, max_size=200):
    """Generate a thumbnail from image data or file path while maintaining aspect ratio.

    Creates a smaller version of the image for efficient display.
    Preserves original format for PNG/WEBP to maintain transparency, otherwise uses JPEG.

    Args:
        image_data (bytes, optional): Raw image data bytes
        image_path (str, optional): Path to image file on disk
        max_size (int, optional): Maximum dimension for thumbnail. Defaults to 200

    Returns:
        bytes or None: Thumbnail data if successful, None if generation fails
            (for non-corruption errors like missing files)

    Raises:
        CorruptedImageError: When image data is corrupted and cannot be processed.
    """
    if not image_data and not image_path:
        logger.warning("generate_thumbnail called without image_data or image_path")
        return None

    if image_path:
        img = Image.open(image_path)
    else:
        img = Image.open(io.BytesIO(image_data))

    # Calculate thumbnail size maintaining aspect ratio
    img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)

    # Determine format and mode
    original_format = img.format
    save_format = original_format if original_format in ('PNG', 'WEBP') else 'JPEG'

    # Handle Alpha channel for JPEG
    if save_format == 'JPEG' and img.mode in ('RGBA', 'P'):
        img = img.convert('RGB')

    # Save thumbnail to bytes
    thumb_buffer = io.BytesIO()
    img.save(thumb_buffer, format=save_format, quality=85)
    return thumb_buffer.getvalue()
