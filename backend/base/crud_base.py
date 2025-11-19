"""Base CRUD class for Flask blueprints."""
from flask import jsonify, request
from typing import Type, Optional, Dict, Any, Callable, List
from sqlalchemy.orm import DeclarativeBase
from shared.validation import Validator, ValidationError
from ..models import db
import logging


class CRUDBase:
    """Base class providing common CRUD operations for Flask blueprints.
    
    This class encapsulates common patterns for:
    - Paginated list retrieval
    - Single resource retrieval
    - Resource creation with validation
    - Resource updates with validation
    - Resource deletion with optional cascade operations
    
    Subclasses should override:
    - serialize() - to customize serialization
    - validate_create_data() - to customize creation validation
    - validate_update_data() - to customize update validation
    - get_singular_name() - to customize resource name
    - get_plural_name() - to customize plural resource name
    """
    
    def __init__(self, model_class: Type[DeclarativeBase], logger_name: Optional[str] = None):
        """Initialize CRUD base class.
        
        Args:
            model_class: SQLAlchemy model class
            logger_name: Optional logger name (defaults to class name)
        """
        self.model = model_class
        self.logger = logging.getLogger(logger_name or self.__class__.__name__)
    
    def get_list(self, page: int = 1, per_page: int = 50, max_per_page: int = 100) -> tuple:
        """Get paginated list of resources.
        
        Args:
            page: Page number (default: 1)
            per_page: Items per page (default: 50)
            max_per_page: Maximum items per page (default: 100)
        
        Returns:
            Flask JSON response with paginated results
        """
        per_page = min(per_page, max_per_page)
        
        pagination = self.model.query.paginate(
            page=page, 
            per_page=per_page, 
            error_out=False
        )
        
        items = [self.serialize(item) for item in pagination.items]
        
        return jsonify({
            self.get_plural_name(): items,
            'pagination': {
                'page': pagination.page,
                'per_page': pagination.per_page,
                'total': pagination.total,
                'pages': pagination.pages,
                'has_next': pagination.has_next,
                'has_prev': pagination.has_prev
            }
        })
    
    def get_detail(self, resource_id: int) -> tuple:
        """Get single resource by ID.
        
        Args:
            resource_id: Primary key ID of the resource
        
        Returns:
            Flask JSON response with resource data
        """
        resource = self.model.query.get_or_404(resource_id)
        return jsonify(self.serialize(resource))
    
    def create(self, validate_func: Optional[Callable] = None) -> tuple:
        """Create a new resource.
        
        Args:
            validate_func: Optional custom validation function that takes data dict
                         and returns validated data dict
        
        Returns:
            Flask JSON response with created resource ID
        """
        try:
            data = self.get_json_data()
            
            if validate_func:
                validated_data = validate_func(data)
            else:
                validated_data = self.validate_create_data(data)
            
            resource = self.model(**validated_data)
            db.session.add(resource)
            db.session.commit()
            
            self.logger.info(f"Created {self.get_singular_name()}: {resource.id} - {getattr(resource, 'name', 'N/A')}")
            
            return jsonify({
                'id': resource.id,
                'message': f'{self.get_singular_name().title()} created successfully'
            }), 201
            
        except ValidationError as e:
            self.logger.warning(f"Validation error in {self.get_singular_name()} creation: {e}")
            return jsonify({'error': str(e)}), 400
        except Exception as e:
            self.logger.error(f"Failed to create {self.get_singular_name()}: {e}", exc_info=True)
            db.session.rollback()
            return jsonify({'error': f'Failed to create {self.get_singular_name()}'}), 500
    
    def update(self, resource_id: int, validate_func: Optional[Callable] = None) -> tuple:
        """Update an existing resource.
        
        Args:
            resource_id: Primary key ID of the resource
            validate_func: Optional custom validation function that takes (data, resource)
                         and returns validated data dict
        
        Returns:
            Flask JSON response with success message
        """
        try:
            data = self.get_json_data()
            resource = self.model.query.get_or_404(resource_id)
            
            if validate_func:
                validated_data = validate_func(data, resource)
            else:
                validated_data = self.validate_update_data(data)
            
            # Update resource attributes
            for key, value in validated_data.items():
                setattr(resource, key, value)
            
            db.session.commit()
            
            self.logger.info(f"Updated {self.get_singular_name()}: {resource_id}")
            return jsonify({'message': f'{self.get_singular_name().title()} updated successfully'})
            
        except ValidationError as e:
            self.logger.warning(f"Validation error in {self.get_singular_name()} update: {e}")
            return jsonify({'error': str(e)}), 400
        except Exception as e:
            self.logger.error(f"Failed to update {self.get_singular_name()}: {e}", exc_info=True)
            db.session.rollback()
            return jsonify({'error': f'Failed to update {self.get_singular_name()}'}), 500
    
    def delete(self, resource_id: int, cascade_func: Optional[Callable] = None) -> tuple:
        """Delete a resource.
        
        Args:
            resource_id: Primary key ID of the resource
            cascade_func: Optional function to handle cascade deletion.
                        Should take resource_id and return summary dict
        
        Returns:
            Flask JSON response with deletion summary
        """
        try:
            resource = self.model.query.get_or_404(resource_id)
            
            if cascade_func:
                summary = cascade_func(resource_id)
            else:
                db.session.delete(resource)
                summary = {}
            
            db.session.commit()
            
            self.logger.info(f"Deleted {self.get_singular_name()}: {resource_id}")
            return jsonify({
                'message': f'{self.get_singular_name().title()} deleted successfully',
                'summary': summary
            })
        except Exception as e:
            self.logger.error(f"Failed to delete {self.get_singular_name()}: {e}", exc_info=True)
            db.session.rollback()
            return jsonify({'error': f'Failed to delete {self.get_singular_name()}'}), 500
    
    def serialize(self, resource: DeclarativeBase) -> Dict[str, Any]:
        """Serialize resource to dictionary.
        
        Subclasses should override this method to customize serialization.
        
        Args:
            resource: SQLAlchemy model instance
        
        Returns:
            Dictionary representation of the resource
        """
        result = {}
        for column in resource.__table__.columns:
            value = getattr(resource, column.name)
            # Handle datetime serialization
            if hasattr(value, 'isoformat'):
                result[column.name] = value.isoformat()
            # Handle enum serialization
            elif hasattr(value, 'value'):
                result[column.name] = value.value
            else:
                result[column.name] = value
        return result
    
    def get_json_data(self) -> Dict[str, Any]:
        """Get and validate JSON data from request.
        
        Returns:
            Dictionary of request JSON data
        
        Raises:
            ValidationError: If JSON is invalid or not a dict
        """
        try:
            data = request.get_json()
            if data is None:
                raise ValidationError('Request body must contain valid JSON')
            if not isinstance(data, dict):
                raise ValidationError('Request data must be a JSON object')
            return data
        except Exception as e:
            if isinstance(e, ValidationError):
                raise
            raise ValidationError('Invalid JSON data')
    
    def validate_create_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate data for creation.
        
        Subclasses should override this method to add custom validation.
        
        Args:
            data: Raw request data dictionary
        
        Returns:
            Validated data dictionary ready for model creation
        
        Raises:
            ValidationError: If validation fails
        """
        return data
    
    def validate_update_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate data for update.
        
        Subclasses should override this method to add custom validation.
        Only fields present in data dict need to be validated.
        
        Args:
            data: Raw request data dictionary
        
        Returns:
            Validated data dictionary ready for model update
        
        Raises:
            ValidationError: If validation fails
        """
        return data
    
    def get_singular_name(self) -> str:
        """Get singular resource name for messages.
        
        Subclasses can override to customize the name.
        
        Returns:
            Singular resource name (e.g., 'project', 'site')
        """
        # Default: remove trailing 's' from table name
        table_name = self.model.__tablename__
        if table_name.endswith('s'):
            return table_name[:-1]
        return table_name
    
    def get_plural_name(self) -> str:
        """Get plural resource name for responses.
        
        Returns:
            Plural resource name (e.g., 'projects', 'sites')
        """
        return self.model.__tablename__

