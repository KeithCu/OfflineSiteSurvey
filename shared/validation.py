"""Input validation utilities."""
import re
import os
from shared.enums import ProjectStatus, SurveyStatus, PriorityLevel

try:
    import bleach
    HAS_BLEACH = True
except ImportError:
    HAS_BLEACH = False


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
    def validate_required(value, field_name):
        """Validate that a required field is not empty."""
        if value is None or (isinstance(value, str) and not value.strip()):
            raise ValidationError(f"{field_name} is required")
        return value

    @staticmethod
    def validate_string_length(value, field_name, min_length=0, max_length=None):
        """Validate string length constraints."""
        if not isinstance(value, str):
            raise ValidationError(f"{field_name} must be a string")

        if len(value) < min_length:
            raise ValidationError(f"{field_name} must be at least {min_length} characters")

        if max_length and len(value) > max_length:
            raise ValidationError(f"{field_name} must be no more than {max_length} characters")

        return value.strip()

    @staticmethod
    def validate_email(email):
        """Validate email format."""
        email = email.strip()
        if not Validator.EMAIL_PATTERN.match(email):
            raise ValidationError("Invalid email format")
        return email

    @staticmethod
    def validate_phone(phone):
        """Validate phone number format."""
        phone = re.sub(r'[^\d+()-.\s]', '', phone.strip())
        if not Validator.PHONE_PATTERN.match(phone):
            raise ValidationError("Invalid phone number format")
        return phone

    @staticmethod
    def validate_coordinates(lat, lng):
        """Validate GPS coordinates.

        Accepts coordinates with reasonable precision (0-10 decimal places).
        GPS coordinates are stored with 6-8 decimal precision internally,
        but input validation should be flexible to accept various formats.
        """
        try:
            lat_val = float(lat) if isinstance(lat, str) else lat
            lng_val = float(lng) if isinstance(lng, str) else lng

            if not (-90 <= lat_val <= 90):
                raise ValidationError("Latitude must be between -90 and 90")

            if not (-180 <= lng_val <= 180):
                raise ValidationError("Longitude must be between -180 and 180")

            # Optional: Validate reasonable precision (avoid excessive decimal places)
            # GPS coordinates typically don't need more than 10 decimal places
            if isinstance(lat, str):
                lat_str = lat.strip()
            else:
                lat_str = f"{lat_val:.10f}".rstrip('0').rstrip('.')

            if '.' in lat_str:
                decimal_places = len(lat_str.split('.')[1])
                if decimal_places > 10:
                    raise ValidationError("Latitude must not have more than 10 decimal places")

            if isinstance(lng, str):
                lng_str = lng.strip()
            else:
                lng_str = f"{lng_val:.10f}".rstrip('0').rstrip('.')

            if '.' in lng_str:
                decimal_places = len(lng_str.split('.')[1])
                if decimal_places > 10:
                    raise ValidationError("Longitude must not have more than 10 decimal places")

            return lat_val, lng_val
        except (ValueError, TypeError):
            raise ValidationError("Invalid coordinate format")

    @staticmethod
    def validate_numeric_range(value, field_name, min_val=None, max_val=None):
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
    def validate_choice(value, field_name, valid_choices):
        """Validate that value is in list of valid choices."""
        if value not in valid_choices:
            raise ValidationError(f"{field_name} must be one of: {', '.join(str(c) for c in valid_choices)}")
        return value

    @staticmethod
    def validate_file_path(file_path, field_name="file path", allow_empty=False):
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
    def sanitize_html(text):
        """Secure HTML sanitization using bleach library."""
        if not text:
            return text
            
        # Use bleach for proper HTML sanitization
        # Allow only safe tags and attributes, no CSS or JavaScript
        allowed_tags = ['p', 'br', 'strong', 'em', 'u', 'ul', 'ol', 'li', 'blockquote']
        allowed_attributes = {}

        return bleach.clean(text, tags=allowed_tags, attributes=allowed_attributes, strip=True)

    @staticmethod
    def validate_project_data(data):
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

        # Validate status and priority
        if 'status' in data:
            validated['status'] = Validator.validate_choice(
                data['status'], 'Project status', [status.value for status in ProjectStatus]
            )
        if 'priority' in data:
            validated['priority'] = Validator.validate_choice(
                data['priority'], 'Project priority', [priority.value for priority in PriorityLevel]
            )

        return validated
    @staticmethod
    def validate_site_data(data):
        """Validate site data."""
        validated = {}

        validated['name'] = Validator.validate_required(
            Validator.validate_string_length(data.get('name', ''), 'Site name', 1, 200),
            'Site name'
        )

        validated['project_id'] = Validator.validate_required(
            Validator.validate_numeric_range(data.get('project_id'), 'Project ID', 1),
            'Project ID'
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
    def validate_survey_data(data):
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
        
        # Validate status
        if 'status' in data:
            validated['status'] = Validator.validate_choice(
                data['status'], 'Survey status', [status.value for status in SurveyStatus]
            )

        return validated
