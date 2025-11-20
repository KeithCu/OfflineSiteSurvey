"""Tests for shared validation utilities."""
import pytest
import os
import tempfile
from shared.validation import Validator, ValidationError
from shared.enums import SurveyStatus


class TestValidator:
    """Test validation utilities."""

    def test_validate_required_success(self):
        """Test successful required field validation."""
        assert Validator.validate_required("test", "test_field") == "test"
        assert Validator.validate_required(123, "test_field") == 123

    def test_validate_required_failure(self):
        """Test required field validation failures."""
        with pytest.raises(ValidationError, match="test_field is required"):
            Validator.validate_required("", "test_field")

        with pytest.raises(ValidationError, match="test_field is required"):
            Validator.validate_required(None, "test_field")

        with pytest.raises(ValidationError, match="test_field is required"):
            Validator.validate_required("   ", "test_field")

    def test_validate_string_length_success(self):
        """Test successful string length validation."""
        assert Validator.validate_string_length("test", "field", 1, 10) == "test"
        assert Validator.validate_string_length("  test  ", "field", 1, 10) == "test"

    def test_validate_string_length_failure(self):
        """Test string length validation failures."""
        with pytest.raises(ValidationError, match="field must be at least 5 characters"):
            Validator.validate_string_length("test", "field", 5, 10)

        with pytest.raises(ValidationError, match="field must be no more than 3 characters"):
            Validator.validate_string_length("testing", "field", 1, 3)

    def test_validate_email_success(self):
        """Test successful email validation."""
        valid_emails = [
            "test@example.com",
            "user.name+tag@example.co.uk",
            "test.email@subdomain.example.com"
        ]
        for email in valid_emails:
            assert Validator.validate_email(email) == email

    def test_validate_email_failure(self):
        """Test email validation failures."""
        invalid_emails = [
            "invalid-email",
            "@example.com",
            "test@",
            "test.example.com"
        ]
        for email in invalid_emails:
            with pytest.raises(ValidationError, match="Invalid email format"):
                Validator.validate_email(email)

    def test_validate_phone_success(self):
        """Test successful phone number validation."""
        valid_phones = [
            "1234567890",
            "(123) 456-7890",
            "123-456-7890",
            "123.456.7890",
            "+1 123-456-7890",
            "+11234567890",
            "1-123-456-7890",
            " 1234567890 ",
            "(123)456-7890"
        ]
        for phone in valid_phones:
            result = Validator.validate_phone(phone)
            # Should return cleaned phone number
            assert result is not None
            assert len(result.replace('+', '').replace('-', '').replace('(', '').replace(')', '').replace('.', '').replace(' ', '')) >= 10

    def test_validate_phone_failure(self):
        """Test phone number validation failures."""
        invalid_phones = [
            "123",
            "12345",
            "abcdefghij",
            "123-456",
            "",
            "   ",
            "12345678901234567890"  # Too long
        ]
        for phone in invalid_phones:
            with pytest.raises(ValidationError, match="Invalid phone number format"):
                Validator.validate_phone(phone)

    @pytest.mark.parametrize("lat,lng,description", [
        (40.7128, -74.0060, "4 decimal places"),
        (40.71280000, -74.00600000, "8 decimal places"),
        (40.7, -74.0, "1 decimal place"),
        (40, -74, "no decimal places"),
        ("40.7128", "-74.0060", "string inputs"),
        (90.0, 180.0, "maximum values"),
        (-90.0, -180.0, "minimum values"),
        (0.0, 0.0, "zero coordinates"),
        (45.123456789, 90.987654321, "high precision within limits"),
    ])
    def test_validate_coordinates_success(self, lat, lng, description):
        """Test successful coordinate validation with various decimal precisions."""
        result_lat, result_lng = Validator.validate_coordinates(lat, lng)
        expected_lat = float(lat) if isinstance(lat, str) else lat
        expected_lng = float(lng) if isinstance(lng, str) else lng
        assert result_lat == expected_lat
        assert result_lng == expected_lng

    def test_validate_coordinates_failure(self):
        """Test coordinate validation failures."""
        # Test range violations
        with pytest.raises(ValidationError, match="Latitude must be between -90 and 90"):
            Validator.validate_coordinates(91, 0)

        with pytest.raises(ValidationError, match="Latitude must be between -90 and 90"):
            Validator.validate_coordinates(-91, 0)

        with pytest.raises(ValidationError, match="Longitude must be between -180 and 180"):
            Validator.validate_coordinates(0, 181)

        with pytest.raises(ValidationError, match="Longitude must be between -180 and 180"):
            Validator.validate_coordinates(0, -181)

        # Test excessive decimal places (>10)
        with pytest.raises(ValidationError, match="Latitude must not have more than 10 decimal places"):
            Validator.validate_coordinates("40.12345678901", "-74.0060")

        with pytest.raises(ValidationError, match="Longitude must not have more than 10 decimal places"):
            Validator.validate_coordinates("40.7128", "-74.12345678901")

        # Test invalid formats
        with pytest.raises(ValidationError, match="Latitude must be a valid number"):
            Validator.validate_coordinates("invalid", "coords")

        with pytest.raises(ValidationError, match="Longitude must be a valid number"):
            Validator.validate_coordinates("40.7128", "invalid")

        with pytest.raises(ValidationError, match="Latitude must be a number or numeric string"):
            Validator.validate_coordinates(None, 0)

        with pytest.raises(ValidationError, match="Longitude must be a number or numeric string"):
            Validator.validate_coordinates(40.7128, None)

    def test_validate_choice_success(self):
        """Test successful choice validation."""
        assert Validator.validate_choice("option1", "field", ["option1", "option2"]) == "option1"

    def test_validate_choice_failure(self):
        """Test choice validation failures."""
        with pytest.raises(ValidationError, match="field must be one of: option1, option2"):
            Validator.validate_choice("option3", "field", ["option1", "option2"])

    def test_validate_numeric_range_success(self):
        """Test successful numeric range validation."""
        # Test with integers
        assert Validator.validate_numeric_range(5, "field", 1, 10) == 5
        assert Validator.validate_numeric_range(1, "field", 1, 10) == 1
        assert Validator.validate_numeric_range(10, "field", 1, 10) == 10

        # Test with floats
        assert Validator.validate_numeric_range(5.5, "field", 1.0, 10.0) == 5.5
        assert Validator.validate_numeric_range(1.0, "field", 1.0, 10.0) == 1.0
        assert Validator.validate_numeric_range(10.0, "field", 1.0, 10.0) == 10.0

        # Test with string numbers
        assert Validator.validate_numeric_range("5", "field", 1, 10) == 5.0
        assert Validator.validate_numeric_range("5.5", "field", 1.0, 10.0) == 5.5

        # Test with only min constraint
        assert Validator.validate_numeric_range(100, "field", 1) == 100

        # Test with only max constraint
        assert Validator.validate_numeric_range(5, "field", None, 10) == 5

        # Test with no constraints
        assert Validator.validate_numeric_range(5, "field") == 5

    def test_validate_numeric_range_failure(self):
        """Test numeric range validation failures."""
        # Test below minimum
        with pytest.raises(ValidationError, match="field must be at least 5"):
            Validator.validate_numeric_range(3, "field", 5, 10)

        # Test above maximum
        with pytest.raises(ValidationError, match="field must be no more than 10"):
            Validator.validate_numeric_range(15, "field", 1, 10)

        # Test invalid string
        with pytest.raises(ValidationError, match="field must be a valid number"):
            Validator.validate_numeric_range("not a number", "field", 1, 10)

        # Test None
        with pytest.raises(ValidationError, match="field must be a valid number"):
            Validator.validate_numeric_range(None, "field", 1, 10)

        # Test empty string
        with pytest.raises(ValidationError, match="field must be a valid number"):
            Validator.validate_numeric_range("", "field", 1, 10)

    def test_validate_project_data_success(self):
        """Test successful project data validation."""
        data = {
            'name': 'Test Project',
            'description': 'A test project',
            'client_info': 'Test Client'
        }
        result = Validator.validate_project_data(data)
        assert result['name'] == 'Test Project'
        assert result['description'] == 'A test project'
        assert result['client_info'] == 'Test Client'

    def test_validate_project_data_failure(self):
        """Test project data validation failures."""
        with pytest.raises(ValidationError, match="Project name must be at least 1 characters"):
            Validator.validate_project_data({})

        with pytest.raises(ValidationError, match="Project name must be at least 1 characters"):
            Validator.validate_project_data({'name': ''})

    def test_validate_site_data_success(self):
        """Test successful site data validation."""
        data = {
            'name': 'Test Site',
            'project_id': 1,
            'address': '123 Test St',
            'notes': 'Test notes',
            'latitude': 40.7128,
            'longitude': -74.0060
        }
        result = Validator.validate_site_data(data)
        assert result['name'] == 'Test Site'
        assert result['project_id'] == 1
        assert result['address'] == '123 Test St'
        assert result['latitude'] == 40.7128
        assert result['longitude'] == -74.0060

    def test_validate_site_data_failure(self):
        """Test site data validation failures."""
        # Missing required name
        with pytest.raises(ValidationError, match="Site name must be at least 1 characters"):
            Validator.validate_site_data({'project_id': 1})

        # Missing required project_id
        with pytest.raises(ValidationError, match="Project ID must be a valid number"):
            Validator.validate_site_data({'name': 'Test Site'})

        # Invalid project_id (too low)
        with pytest.raises(ValidationError, match="Project ID must be at least 1"):
            Validator.validate_site_data({'name': 'Test Site', 'project_id': 0})

        # Invalid coordinates
        with pytest.raises(ValidationError, match="Latitude must be between -90 and 90"):
            Validator.validate_site_data({
                'name': 'Test Site',
                'project_id': 1,
                'latitude': 91,
                'longitude': 0
            })

    def test_sanitize_html(self):
        """Test HTML sanitization."""
        # Test script tag removal - bleach removes script tags but may keep content
        result = Validator.sanitize_html("<script>alert('xss')</script>Hello")
        assert "Hello" in result
        assert "<script>" not in result

        # Test normal text passes through
        assert Validator.sanitize_html("Normal text") == "Normal text"

        # Test javascript URL removal - bleach removes javascript: URLs
        result = Validator.sanitize_html('<a href="javascript:alert()">Link</a>')
        assert "javascript:" not in result.lower()

        # Test empty/None values
        assert Validator.sanitize_html("") == ""
        assert Validator.sanitize_html(None) is None

        # Test allowed tags pass through
        assert "<p>Test</p>" in Validator.sanitize_html("<p>Test</p>")
        assert "<strong>Bold</strong>" in Validator.sanitize_html("<strong>Bold</strong>")
        assert "<em>Italic</em>" in Validator.sanitize_html("<em>Italic</em>")

        # Test dangerous tags are removed
        result = Validator.sanitize_html("<iframe src='evil.com'>Test</iframe>")
        assert "<iframe>" not in result
        assert "Test" in result
        
        result = Validator.sanitize_html("<object>Test</object>")
        assert "<object>" not in result
        assert "Test" in result
        
        result = Validator.sanitize_html("<embed>Test</embed>")
        assert "<embed>" not in result
        assert "Test" in result

        # Test text without HTML tags (fast path)
        assert Validator.sanitize_html("Plain text without tags") == "Plain text without tags"
        # Note: bleach escapes & to &amp; when HTML parsing is involved
        # But our fast path should return as-is if no < > & chars
        assert Validator.sanitize_html("Text without special chars") == "Text without special chars"

    def test_validate_file_path_success(self):
        """Test successful file path validation."""
        # Create a temporary file in current directory for testing (relative path)
        with tempfile.NamedTemporaryFile(delete=False, dir='.') as tmp_file:
            tmp_path = os.path.basename(tmp_file.name)

        try:
            # Test valid relative file path
            result = Validator.validate_file_path(tmp_path, "test file")
            assert result == tmp_path

            # Test with allow_empty=True and empty path
            result = Validator.validate_file_path("", "test file", allow_empty=True)
            assert result is None

            # Test with allow_empty=True and None
            result = Validator.validate_file_path(None, "test file", allow_empty=True)
            assert result is None
        finally:
            # Clean up
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def test_validate_file_path_failure(self):
        """Test file path validation failures."""
        # Test empty path without allow_empty
        with pytest.raises(ValidationError, match="file path is required"):
            Validator.validate_file_path("", "file path")

        # Test None without allow_empty
        with pytest.raises(ValidationError, match="file path is required"):
            Validator.validate_file_path(None, "file path")

        # Test path traversal attempt
        with pytest.raises(ValidationError, match="path traversal not allowed"):
            Validator.validate_file_path("../etc/passwd", "file path")

        with pytest.raises(ValidationError, match="path traversal not allowed"):
            Validator.validate_file_path("../../secret", "file path")

        # Test absolute path
        with pytest.raises(ValidationError, match="path traversal not allowed"):
            Validator.validate_file_path("/etc/passwd", "file path")

        # Test dangerous characters
        dangerous_chars = ['<', '>', '|', '&', ';', '$', '`']
        for char in dangerous_chars:
            with pytest.raises(ValidationError, match="Invalid characters"):
                Validator.validate_file_path(f"test{char}file.txt", "file path")

        # Test non-existent file
        with pytest.raises(ValidationError, match="does not exist"):
            Validator.validate_file_path("nonexistent_file_12345.txt", "file path")

    def test_validate_survey_data_success(self):
        """Test successful survey data validation."""
        data = {
            'title': 'Test Survey',
            'description': 'A test survey',
            'site_id': 1,
            'status': 'draft'
        }
        result = Validator.validate_survey_data(data)
        assert result['title'] == 'Test Survey'
        assert result['description'] == 'A test survey'
        assert result['site_id'] == 1
        assert result['status'] == 'draft'

        # Test with all status values
        for status in SurveyStatus:
            data = {
                'title': 'Test Survey',
                'site_id': 1,
                'status': status.value
            }
            result = Validator.validate_survey_data(data)
            assert result['status'] == status.value

    def test_validate_survey_data_failure(self):
        """Test survey data validation failures."""
        # Missing required title
        with pytest.raises(ValidationError, match="Survey title must be at least 1 characters"):
            Validator.validate_survey_data({'site_id': 1})

        # Missing required site_id
        with pytest.raises(ValidationError, match="Site ID must be a valid number"):
            Validator.validate_survey_data({'title': 'Test Survey'})

        # Invalid site_id (too low)
        with pytest.raises(ValidationError, match="Site ID must be at least 1"):
            Validator.validate_survey_data({'title': 'Test Survey', 'site_id': 0})

        # Invalid status
        with pytest.raises(ValidationError, match="Survey status must be one of"):
            Validator.validate_survey_data({
                'title': 'Test Survey',
                'site_id': 1,
                'status': 'invalid_status'
            })

        # Empty title
        with pytest.raises(ValidationError, match="Survey title must be at least 1 characters"):
            Validator.validate_survey_data({'title': '', 'site_id': 1})

    def test_validate_project_data_comprehensive(self):
        """Test comprehensive project data validation."""
        # Test with all fields including status and priority
        data = {
            'name': 'Test Project',
            'description': 'A test project',
            'client_info': 'Test Client',
            'status': 'draft',
            'priority': 'high'
        }
        result = Validator.validate_project_data(data)
        assert result['name'] == 'Test Project'
        assert result['description'] == 'A test project'
        assert result['client_info'] == 'Test Client'
        assert result['status'] == 'draft'
        assert result['priority'] == 'high'

        # Test with HTML in client_info (should be sanitized)
        data = {
            'name': 'Test Project',
            'client_info': '<script>alert("xss")</script>Safe text'
        }
        result = Validator.validate_project_data(data)
        assert 'Safe text' in result['client_info']
        assert '<script>' not in result['client_info']

        # Test invalid status
        with pytest.raises(ValidationError, match="Project status must be one of"):
            Validator.validate_project_data({
                'name': 'Test Project',
                'status': 'invalid_status'
            })

        # Test invalid priority
        with pytest.raises(ValidationError, match="Project priority must be one of"):
            Validator.validate_project_data({
                'name': 'Test Project',
                'priority': 'invalid_priority'
            })

        # Test name too long
        with pytest.raises(ValidationError, match="Project name must be no more than 200 characters"):
            Validator.validate_project_data({
                'name': 'a' * 201
            })

        # Test description too long
        with pytest.raises(ValidationError, match="Project description must be no more than 1000 characters"):
            Validator.validate_project_data({
                'name': 'Test Project',
                'description': 'a' * 1001
            })
