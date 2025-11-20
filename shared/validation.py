"""Input validation utilities."""
import re
import os
import bleach
from shared.enums import ProjectStatus, SurveyStatus, PriorityLevel


class ValidationError(Exception):
    """Raised when input validation fails."""
    pass


class Validator:
    """Input validation utilities."""

    # Common validation patterns (pre-compiled for performance)
    # Email pattern: local part must start/end with alphanumeric, no consecutive dots/special chars
    # Domain parts must start/end with alphanumeric, no consecutive dots/hyphens
    EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9]+([._%+-][a-zA-Z0-9]+)*@([a-zA-Z0-9]+([.-][a-zA-Z0-9]+)*\.)+[a-zA-Z]{2,}$')
    PHONE_PATTERN = re.compile(r'^\+?1?[-.\s]?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})$')
    PHONE_CLEAN_PATTERN = re.compile(r'[^\d+()-.\s]')  # Pre-compiled for phone cleaning
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
        """Validate phone number format.
        
        Optimized: strip first, then apply regex substitution.
        """
        phone_stripped = phone.strip()
        # Only apply regex if there are non-digit characters to remove
        # Most phone numbers are already clean, so this avoids regex overhead
        if any(c not in '0123456789+()-.' for c in phone_stripped):
            phone_stripped = Validator.PHONE_CLEAN_PATTERN.sub('', phone_stripped)
        if not Validator.PHONE_PATTERN.match(phone_stripped):
            raise ValidationError("Invalid phone number format")
        return phone_stripped

    @staticmethod
    def validate_coordinates(lat, lng):
        """Validate GPS coordinates.

        Accepts coordinates with reasonable precision (0-10 decimal places).
        GPS coordinates are stored with 6-8 decimal precision internally,
        but input validation should be flexible to accept various formats.
        
        Optimized to minimize string operations and conversions.
        """
        # Validate and convert latitude
        try:
            if isinstance(lat, str):
                lat_stripped = lat.strip()
                # Check decimal precision before conversion
                if '.' in lat_stripped:
                    decimal_part = lat_stripped.split('.', 1)[1]
                    # Remove trailing zeros before counting
                    decimal_part = decimal_part.rstrip('0')
                    if decimal_part and len(decimal_part) > 10:
                        raise ValidationError("Latitude must not have more than 10 decimal places")
                # Attempt conversion - will raise ValueError if invalid
                lat_val = float(lat_stripped)
            else:
                lat_val = float(lat)
        except ValueError:
            raise ValidationError("Latitude must be a valid number")
        except TypeError:
            raise ValidationError("Latitude must be a number or numeric string")

        # Validate and convert longitude
        try:
            if isinstance(lng, str):
                lng_stripped = lng.strip()
                # Check decimal precision before conversion
                if '.' in lng_stripped:
                    decimal_part = lng_stripped.split('.', 1)[1]
                    # Remove trailing zeros before counting
                    decimal_part = decimal_part.rstrip('0')
                    if decimal_part and len(decimal_part) > 10:
                        raise ValidationError("Longitude must not have more than 10 decimal places")
                # Attempt conversion - will raise ValueError if invalid
                lng_val = float(lng_stripped)
            else:
                lng_val = float(lng)
        except ValueError:
            raise ValidationError("Longitude must be a valid number")
        except TypeError:
            raise ValidationError("Longitude must be a number or numeric string")

        # Validate ranges
        if not (-90 <= lat_val <= 90):
            raise ValidationError("Latitude must be between -90 and 90")

        if not (-180 <= lng_val <= 180):
            raise ValidationError("Longitude must be between -180 and 180")

        # Check precision for float values (already checked for strings above)
        if not isinstance(lat, str) and lat_val != int(lat_val):
            # Float has decimal component, check precision
            lat_str = f"{lat_val:.10f}".rstrip('0').rstrip('.')
            if '.' in lat_str:
                decimal_places = len(lat_str.split('.', 1)[1])
                if decimal_places > 10:
                    raise ValidationError("Latitude must not have more than 10 decimal places")

        if not isinstance(lng, str) and lng_val != int(lng_val):
            # Float has decimal component, check precision
            lng_str = f"{lng_val:.10f}".rstrip('0').rstrip('.')
            if '.' in lng_str:
                decimal_places = len(lng_str.split('.', 1)[1])
                if decimal_places > 10:
                    raise ValidationError("Longitude must not have more than 10 decimal places")

        return lat_val, lng_val

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

        # Check file existence if a path is provided
        if file_path and not os.path.exists(file_path):
            raise ValidationError(f"{field_name} does not exist: {file_path}")

        return file_path

    @staticmethod
    def sanitize_html(text):
        """Secure HTML sanitization using bleach library.
        
        Optimized with early returns for simple cases to avoid expensive
        HTML parsing when not needed.
        """
        if not text:
            return text
        
        # Fast path: if text contains no HTML tags or special characters, return as-is
        # This avoids expensive bleach parsing for plain text (common case)
        if '<' not in text and '>' not in text and '&' not in text:
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
