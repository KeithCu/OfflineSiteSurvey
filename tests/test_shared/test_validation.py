"""Tests for shared validation utilities."""
import pytest
from shared.validation import Validator, ValidationError


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

    def test_validate_coordinates_success(self):
        """Test successful coordinate validation."""
        lat, lng = Validator.validate_coordinates(40.7128, -74.0060)
        assert lat == 40.7128
        assert lng == -74.0060

    def test_validate_coordinates_failure(self):
        """Test coordinate validation failures."""
        with pytest.raises(ValidationError, match="Latitude must be between -90 and 90"):
            Validator.validate_coordinates(91, 0)

        with pytest.raises(ValidationError, match="Longitude must be between -180 and 180"):
            Validator.validate_coordinates(0, 181)

    def test_validate_choice_success(self):
        """Test successful choice validation."""
        assert Validator.validate_choice("option1", "field", ["option1", "option2"]) == "option1"

    def test_validate_choice_failure(self):
        """Test choice validation failures."""
        with pytest.raises(ValidationError, match="field must be one of: option1, option2"):
            Validator.validate_choice("option3", "field", ["option1", "option2"])

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
            'address': '123 Test St',
            'notes': 'Test notes',
            'latitude': 40.7128,
            'longitude': -74.0060
        }
        result = Validator.validate_site_data(data)
        assert result['name'] == 'Test Site'
        assert result['latitude'] == 40.7128
        assert result['longitude'] == -74.0060

    def test_sanitize_html(self):
        """Test HTML sanitization."""
        # Test script tag removal
        assert Validator.sanitize_html("<script>alert('xss')</script>Hello") == "Hello"

        # Test normal text passes through
        assert Validator.sanitize_html("Normal text") == "Normal text"

        # Test javascript URL removal
        assert Validator.sanitize_html('<a href="javascript:alert()">Link</a>') == '<a href="">Link</a>'
