"""Shared utility functions for Site Survey application.

This module contains utility functions used across both backend and frontend
components of the Site Survey application.
"""

import hashlib
import json
from PIL import Image
import io


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
        return hashlib.new(algo, image_data).hexdigest()
    return None


def should_show_field(conditions, responses):
    """Evaluate conditional logic to determine if a survey field should be displayed.

    Supports AND/OR logic with various comparison operators for building
    dynamic survey forms based on previous responses.

    Args:
        conditions (dict): Condition specification with 'conditions' list and 'logic' key
            Format: {
                'conditions': [
                    {'question_id': str, 'operator': str, 'value': any}
                ],
                'logic': 'AND' | 'OR'
            }
        responses (list): List of response dictionaries with 'question_id' and 'answer' keys

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
        >>> should_show_field(conditions, responses)
        True
    """
    if not conditions:
        return True

    condition_list = conditions.get('conditions', [])
    logic = conditions.get('logic', 'AND')

    results = []
    for condition in condition_list:
        question_id = condition['question_id']
        operator = condition['operator']
        expected_value = condition['value']

        # Find response for this question
        response = next((r for r in responses if r.get('question_id') == question_id), None)
        if not response:
            results.append(False)
            continue

        actual_value = response.get('answer')

        if operator == 'equals':
            results.append(str(actual_value) == str(expected_value))
        elif operator == 'not_equals':
            results.append(str(actual_value) != str(expected_value))
        elif operator == 'in':
            results.append(str(actual_value) in [str(v) for v in expected_value])
        elif operator == 'not_in':
            results.append(str(actual_value) not in [str(v) for v in expected_value])

    return all(results) if logic == 'AND' else any(results)


def generate_thumbnail(image_data, max_size=200):
    """Generate a thumbnail from image data while maintaining aspect ratio.

    Creates a smaller JPEG version of the image for efficient display in galleries
    and lists. Used during photo upload to create cached thumbnails.

    Args:
        image_data (bytes): Raw image data bytes
        max_size (int, optional): Maximum dimension for thumbnail. Defaults to 200

    Returns:
        bytes or None: JPEG thumbnail data if successful, None if generation fails

    Note:
        Thumbnails are saved with 85% JPEG quality for reasonable size/performance balance.
        PIL Image.Resampling.LANCZOS is used for high-quality downsampling.

    Examples:
        >>> from PIL import Image
        >>> import io
        >>> img = Image.new('RGB', (1000, 800), color='blue')
        >>> buf = io.BytesIO()
        >>> img.save(buf, format='JPEG')
        >>> thumb = generate_thumbnail(buf.getvalue(), max_size=100)
        >>> thumb is not None
        True
    """
    if not image_data:
        return None

    try:
        img = Image.open(io.BytesIO(image_data))

        # Calculate thumbnail size maintaining aspect ratio
        img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)

        # Save thumbnail to bytes
        thumb_buffer = io.BytesIO()
        img.save(thumb_buffer, format='JPEG', quality=85)
        return thumb_buffer.getvalue()
    except Exception:
        # Log error but don't expose internal details
        return None
