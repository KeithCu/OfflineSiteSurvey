"""Generic CRUD class that works with Pydantic schemas to eliminate boilerplate."""
from flask import jsonify, request
from sqlalchemy.orm import DeclarativeBase
from shared.validation import ValidationError
from ..models import db
from pydantic import ValidationError as PydanticValidationError
import logging
from typing import Optional, Callable, Any, Dict


class GenericCRUD:
    """Generic CRUD class that automatically handles Pydantic validation and serialization.
    
    This class eliminates boilerplate by accepting Pydantic schemas as constructor
    parameters and automatically handling validation and serialization.
    
    Usage:
        crud = GenericCRUD(
            model=Project,
            create_schema=ProjectCreate,
            update_schema=ProjectUpdate,
            response_schema=ProjectResponse,
            logger_name='projects'
        )
    """
    
    def __init__(
        self,
        model: type,
        create_schema: type,
        update_schema: type,
        response_schema: type,
        logger_name: Optional[str] = None,
        pre_create_hook: Optional[Callable[[Dict], Dict]] = None,
        pre_update_hook: Optional[Callable[[Dict, Any], Dict]] = None,
        serialize_hook: Optional[Callable[[Any], Dict]] = None,
        cascade_delete_func: Optional[Callable[[int], Dict]] = None
    ):
        """Initialize generic CRUD class.
        
        Args:
            model: SQLAlchemy model class
            create_schema: Pydantic schema for creation (e.g., ProjectCreate)
            update_schema: Pydantic schema for updates (e.g., ProjectUpdate)
            response_schema: Pydantic schema for responses (e.g., ProjectResponse)
            logger_name: Optional logger name (defaults to model table name)
            pre_create_hook: Optional function to run after Pydantic validation but before creation.
                           Takes validated_data dict, returns modified dict.
            pre_update_hook: Optional function to run after Pydantic validation but before update.
                           Takes (validated_data, resource) tuple, returns modified dict.
            serialize_hook: Optional function to customize serialization.
                           Takes resource instance, returns dict. If provided, overrides default.
            cascade_delete_func: Optional function to handle cascade deletion.
                               Takes resource_id, returns summary dict.
        """
        self.model = model
        self.create_schema = create_schema
        self.update_schema = update_schema
        self.response_schema = response_schema
        self.pre_create_hook = pre_create_hook
        self.pre_update_hook = pre_update_hook
        self.serialize_hook = serialize_hook
        self.cascade_delete_func = cascade_delete_func
        self.logger = logging.getLogger(logger_name or model.__tablename__)
    
    def get_list(self, page=1, per_page=50, max_per_page=100):
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
    
    def get_detail(self, resource_id):
        """Get single resource by ID.
        
        Args:
            resource_id: Primary key ID of the resource
        
        Returns:
            Flask JSON response with resource data
        """
        resource = self.model.query.get_or_404(resource_id)
        return jsonify(self.serialize(resource))
    
    def create(self):
        """Create a new resource with automatic Pydantic validation.
        
        Returns:
            Flask JSON response with created resource ID
        """
        try:
            data = self.get_json_data()
            validated_data = self.validate_create_data(data)
            
            if self.pre_create_hook:
                validated_data = self.pre_create_hook(validated_data)
            
            resource = self.model(**validated_data)
            db.session.add(resource)
            db.session.commit()
            
            self.logger.info(f"Created {self.get_singular_name()}: {resource.id} - {getattr(resource, 'name', getattr(resource, 'title', 'N/A'))}")
            
            response_data = {'id': resource.id, 'message': f'{self.get_singular_name().title()} created successfully'}
            
            if hasattr(resource, 'template_id'):
                response_data['template_id'] = resource.template_id
            
            return jsonify(response_data), 201
            
        except ValidationError as e:
            self.logger.warning(f"Validation error in {self.get_singular_name()} creation: {e}")
            return jsonify({'error': str(e)}), 400
        except Exception as e:
            self.logger.error(f"Failed to create {self.get_singular_name()}: {e}", exc_info=True)
            db.session.rollback()
            return jsonify({'error': f'Failed to create {self.get_singular_name()}'}), 500
    
    def update(self, resource_id):
        """Update an existing resource with automatic Pydantic validation.
        
        Args:
            resource_id: Primary key ID of the resource
        
        Returns:
            Flask JSON response with success message
        """
        try:
            data = self.get_json_data()
            resource = self.model.query.get_or_404(resource_id)
            
            validated_data = self.validate_update_data(data)
            
            if self.pre_update_hook:
                validated_data = self.pre_update_hook(validated_data, resource)
            
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
    
    def delete(self, resource_id):
        """Delete a resource.
        
        Args:
            resource_id: Primary key ID of the resource
        
        Returns:
            Flask JSON response with deletion summary
        """
        try:
            resource = self.model.query.get_or_404(resource_id)
            
            if self.cascade_delete_func:
                summary = self.cascade_delete_func(resource_id)
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
    
    def serialize(self, resource):
        """Serialize resource using Pydantic response schema.
        
        Args:
            resource: SQLAlchemy model instance
        
        Returns:
            Dictionary representation of the resource
        """
        if self.serialize_hook:
            return self.serialize_hook(resource)
        
        return self.response_schema.model_validate(resource).model_dump(mode='json')
    
    def validate_create_data(self, data):
        """Validate data for creation using Pydantic schema.
        
        Args:
            data: Raw request data dictionary
        
        Returns:
            Validated data dictionary ready for model creation
        
        Raises:
            ValidationError: If validation fails
        """
        try:
            validated = self.create_schema(**data)
            return validated.model_dump(exclude_none=True)
        except PydanticValidationError as e:
            errors = []
            for error in e.errors():
                field = '.'.join(str(x) for x in error['loc'])
                msg = error['msg']
                errors.append(f"{field}: {msg}")
            raise ValidationError('; '.join(errors))
    
    def validate_update_data(self, data):
        """Validate data for update using Pydantic schema.
        
        Args:
            data: Raw request data dictionary
        
        Returns:
            Validated data dictionary ready for model update
        
        Raises:
            ValidationError: If validation fails
        """
        try:
            validated = self.update_schema(**data)
            return validated.model_dump(exclude_none=True)
        except PydanticValidationError as e:
            errors = []
            for error in e.errors():
                field = '.'.join(str(x) for x in error['loc'])
                msg = error['msg']
                errors.append(f"{field}: {msg}")
            raise ValidationError('; '.join(errors))
    
    def get_json_data(self):
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
    
    def get_singular_name(self):
        """Get singular resource name for messages.
        
        Returns:
            Singular resource name (e.g., 'project', 'site')
        """
        table_name = self.model.__tablename__
        if table_name.endswith('s'):
            return table_name[:-1]
        return table_name
    
    def get_plural_name(self):
        """Get plural resource name for responses.
        
        Returns:
            Plural resource name (e.g., 'projects', 'sites')
        """
        return self.model.__tablename__


def register_crud_routes(bp, crud_instance, resource_name, id_type=int):
    """Register standard CRUD routes for a blueprint.
    
    Args:
        bp: Flask Blueprint instance
        crud_instance: GenericCRUD instance
        resource_name: Name of the resource (e.g., 'projects', 'sites')
        id_type: Type of ID parameter (int or str, default: int)
    
    This function registers:
        GET /api/{resource_name} - List resources
        GET /api/{resource_name}/<id> - Get single resource
        POST /api/{resource_name} - Create resource
        PUT /api/{resource_name}/<id> - Update resource
        DELETE /api/{resource_name}/<id> - Delete resource
    """
    id_type_name = 'int' if id_type == int else 'str'
    id_param = f'<{id_type_name}:{resource_name.rstrip("s")}_id>'
    
    @bp.route(f'/{resource_name}', methods=['GET'])
    def get_list():
        """Get paginated list of resources."""
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 50, type=int), 100)
        return crud_instance.get_list(page=page, per_page=per_page)
    
    @bp.route(f'/{resource_name}/{id_param}', methods=['GET'])
    def get_detail(resource_id):
        """Get single resource by ID."""
        return crud_instance.get_detail(resource_id)
    
    @bp.route(f'/{resource_name}', methods=['POST'])
    def create():
        """Create a new resource."""
        return crud_instance.create()
    
    @bp.route(f'/{resource_name}/{id_param}', methods=['PUT'])
    def update(resource_id):
        """Update an existing resource."""
        return crud_instance.update(resource_id)
    
    @bp.route(f'/{resource_name}/{id_param}', methods=['DELETE'])
    def delete(resource_id):
        """Delete a resource."""
        return crud_instance.delete(resource_id)

