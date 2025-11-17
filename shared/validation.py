"""Input validation utilities."""
import re
import os
from typing import Any, Optional, Union, List


class ValidationError(Exception):
    """Raised when input validation fails."""
    pass


class Validator:
    """Input validation utilities."""

    # Common validation patterns
    EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    PHONE_PATTERN = re.compile(r'^\+?1?[-.\s]?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})$')
    ZIP_PATTERN = re.compile(r'^\d{5}(-\d{4})?$')
    COORDINATE_PATTERN = re.compile(r'^-?([1-8]?\d(\.\d+)?|90(\.0+)?),\s*-?(180(\.0+)?|((1[0-7]\d)|([1-9]?\d))(\.\d+)?)$')

    @staticmethod
    def validate_required(value: Any, field_name: str) -> Any:
        """Validate that a required field is not empty."""
        if value is None or (isinstance(value, str) and not value.strip()):
            raise ValidationError(f"{field_name} is required")
        return value

    @staticmethod
    def validate_string_length(value: str, field_name: str, min_length: int = 0, max_length: int = None) -> str:
        """Validate string length constraints."""
        if not isinstance(value, str):
            raise ValidationError(f"{field_name} must be a string")

        if len(value) < min_length:
            raise ValidationError(f"{field_name} must be at least {min_length} characters")

        if max_length and len(value) > max_length:
            raise ValidationError(f"{field_name} must be no more than {max_length} characters")

        return value.strip()

    @staticmethod
    def validate_email(email: str) -> str:
        """Validate email format."""
        email = email.strip()
        if not Validator.EMAIL_PATTERN.match(email):
            raise ValidationError("Invalid email format")
        return email

    @staticmethod
    def validate_phone(phone: str) -> str:
        """Validate phone number format."""
        phone = re.sub(r'[^\d+()-.\s]', '', phone.strip())
        if not Validator.PHONE_PATTERN.match(phone):
            raise ValidationError("Invalid phone number format")
        return phone

    @staticmethod
    def validate_coordinates(lat: Union[str, float], lng: Union[str, float]) -> tuple[float, float]:
        """Validate GPS coordinates."""
        try:
            lat_val = float(lat) if isinstance(lat, str) else lat
            lng_val = float(lng) if isinstance(lng, str) else lng

            if not (-90 <= lat_val <= 90):
                raise ValidationError("Latitude must be between -90 and 90")

            if not (-180 <= lng_val <= 180):
                raise ValidationError("Longitude must be between -180 and 180")

            return lat_val, lng_val
        except (ValueError, TypeError):
            raise ValidationError("Invalid coordinate format")

    @staticmethod
    def validate_numeric_range(value: Union[str, int, float], field_name: str,
                             min_val: Union[int, float] = None, max_val: Union[int, float] = None) -> Union[int, float]:
        """Validate numeric value within range."""
        try:
            num_val = float(value) if isinstance(value, str) else value

            if min_val is not None and num_val < min_val:
                raise ValidationError(f"{field_name} must be at least {min_val}")

            if max_val is not None and num_val > max_val:
                raise ValidationError(f"{field_name} must be no more than {max_val}")

            return num_val
        except (ValueError, TypeError):
            raise ValidationError(f"{field_name} must be a valid number")

    @staticmethod
    def validate_choice(value: Any, field_name: str, valid_choices: List[Any]) -> Any:
        """Validate that value is in list of valid choices."""
        if value not in valid_choices:
            raise ValidationError(f"{field_name} must be one of: {', '.join(str(c) for c in valid_choices)}")
        return value

    @staticmethod
    def validate_file_path(file_path: str, field_name: str = "file path", allow_empty: bool = False) -> Optional[str]:
        """Validate file path security and existence."""
        if not file_path and allow_empty:
            return None

        if not file_path:
            raise ValidationError(f"{field_name} is required")

        # Security checks - prevent directory traversal
        if '..' in file_path or file_path.startswith('/'):
            raise ValidationError(f"Invalid {field_name} - path traversal not allowed")

        # Check for dangerous characters
        dangerous_chars = ['<', '>', '|', '&', ';', '$', '`']
        if any(char in file_path for char in dangerous_chars):
            raise ValidationError(f"Invalid characters in {field_name}")

        return file_path

    @staticmethod
    def sanitize_html(text: str) -> str:
        """Basic HTML sanitization - remove potentially dangerous tags."""
        if not text:
            return text

        # Remove script tags and their contents
        text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.IGNORECASE | re.DOTALL)

        # Remove other potentially dangerous tags
        dangerous_tags = ['iframe', 'object', 'embed', 'form', 'input', 'button']
        for tag in dangerous_tags:
            text = re.sub(rf'<{tag}[^>]*>.*?</{tag}>', '', text, flags=re.IGNORECASE | re.DOTALL)

        # Remove javascript: URLs
        text = re.sub(r'javascript:[^"\'>\s]*', '', text, flags=re.IGNORECASE)

        return text

    @staticmethod
    def validate_project_data(data: dict) -> dict:
        """Validate project data."""
        validated = {}

        validated['name'] = Validator.validate_required(
            Validator.validate_string_length(data.get('name', ''), 'Project name', 1, 200),
            'Project name'
        )

        if 'description' in data:
            validated['description'] = Validator.validate_string_length(
                data['description'], 'Project description', 0, 1000
            )

        if 'client_info' in data:
            validated['client_info'] = Validator.sanitize_html(
                Validator.validate_string_length(data['client_info'], 'Client info', 0, 500)
            )

        return validated

    @staticmethod
    def validate_site_data(data: dict) -> dict:
        """Validate site data."""
        validated = {}

        validated['name'] = Validator.validate_required(
            Validator.validate_string_length(data.get('name', ''), 'Site name', 1, 200),
            'Site name'
        )

        if 'address' in data:
            validated['address'] = Validator.validate_string_length(
                data['address'], 'Site address', 0, 500
            )

        if 'notes' in data:
            validated['notes'] = Validator.sanitize_html(
                Validator.validate_string_length(data['notes'], 'Site notes', 0, 1000)
            )

        # Validate coordinates if provided
        if 'latitude' in data and 'longitude' in data:
            validated['latitude'], validated['longitude'] = Validator.validate_coordinates(
                data['latitude'], data['longitude']
            )

        return validated

    @staticmethod
    def validate_survey_data(data: dict) -> dict:
        """Validate survey data."""
        validated = {}

        validated['title'] = Validator.validate_required(
            Validator.validate_string_length(data.get('title', ''), 'Survey title', 1, 200),
            'Survey title'
        )

        if 'description' in data:
            validated['description'] = Validator.validate_string_length(
                data['description'], 'Survey description', 0, 1000
            )

        validated['site_id'] = Validator.validate_required(
            Validator.validate_numeric_range(data.get('site_id'), 'Site ID', 1),
            'Site ID'
        )

        return validated
