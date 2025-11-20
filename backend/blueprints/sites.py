"""Sites blueprint for Flask API."""
from flask import Blueprint, request, jsonify
from ..models import Site
from ..base.crud_base import CRUDBase
from shared.validation import Validator, ValidationError
from ..utils import validate_foreign_key
bp = Blueprint('sites', __name__, url_prefix='/api')


class SiteCRUD(CRUDBase):
    """CRUD operations for Site model."""
    
    def __init__(self):
        super().__init__(Site, logger_name='sites')
    
    def serialize(self, site, include_project_id=True):
        """Serialize site to dictionary.
        
        Args:
            site: Site model instance
            include_project_id: Whether to include project_id in response
        """
        result = {
            'id': site.id,
            'name': site.name,
            'address': site.address,
            'latitude': site.latitude,
            'longitude': site.longitude,
            'notes': site.notes,
            'created_at': site.created_at.isoformat(),
            'updated_at': site.updated_at.isoformat()
        }
        
        if include_project_id:
            result['project_id'] = site.project_id
        
        return result
    
    def validate_create_data(self, data):
        """Validate and prepare data for site creation."""
        # Validate input data using shared validator
        validated_data = Validator.validate_site_data(data)
        
        # Validate that project_id exists
        project_id = validated_data['project_id']
        if not validate_foreign_key('projects', 'id', project_id):
            raise ValidationError(f'Project with ID {project_id} does not exist')
        
        # Clean up string fields
        if 'name' in validated_data:
            validated_data['name'] = validated_data['name'].strip()
        
        if 'address' in validated_data:
            address = validated_data['address']
            validated_data['address'] = address.strip() if address else None
        
        if 'notes' in validated_data:
            notes = validated_data['notes']
            validated_data['notes'] = notes.strip() if notes else None
        
        # Set default coordinates if not provided
        if 'latitude' not in validated_data:
            validated_data['latitude'] = 0.0
        if 'longitude' not in validated_data:
            validated_data['longitude'] = 0.0
        
        return validated_data
    
    def validate_update_data(self, data):
        """Validate and prepare data for site update."""
        validated_data = {}
        
        # Validate and prepare name
        if 'name' in data:
            name = data['name']
            if not isinstance(name, str) or not name.strip():
                raise ValidationError('name must be a non-empty string')
            validated_data['name'] = name.strip()
        
        # Validate and prepare project_id
        if 'project_id' in data:
            project_id = data['project_id']
            if project_id is not None:
                try:
                    project_id = int(project_id)
                except (ValueError, TypeError):
                    raise ValidationError('project_id must be an integer')
                
                if not validate_foreign_key('projects', 'id', project_id):
                    raise ValidationError(f'project_id {project_id} does not exist')
            validated_data['project_id'] = project_id
        
        # Validate and prepare address
        if 'address' in data:
            address = data['address']
            if address is not None and not isinstance(address, str):
                raise ValidationError('address must be a string')
            validated_data['address'] = address.strip() if address else None
        
        # Validate and prepare latitude
        if 'latitude' in data:
            latitude = data['latitude']
            if latitude is not None:
                try:
                    latitude = float(latitude)
                    if not (-90 <= latitude <= 90):
                        raise ValidationError('latitude must be between -90 and 90')
                except (ValueError, TypeError):
                    raise ValidationError('latitude must be a number')
            validated_data['latitude'] = latitude
        
        # Validate and prepare longitude
        if 'longitude' in data:
            longitude = data['longitude']
            if longitude is not None:
                try:
                    longitude = float(longitude)
                    if not (-180 <= longitude <= 180):
                        raise ValidationError('longitude must be between -180 and 180')
                except (ValueError, TypeError):
                    raise ValidationError('longitude must be a number')
            validated_data['longitude'] = longitude
        
        # Validate and prepare notes
        if 'notes' in data:
            notes = data['notes']
            if notes is not None and not isinstance(notes, str):
                raise ValidationError('notes must be a string')
            validated_data['notes'] = notes.strip() if notes else None
        
        return validated_data
    
    def get_list(self, page=1, per_page=50, max_per_page=100):
        """Get paginated list of sites (with project_id included)."""
        per_page = min(per_page, max_per_page)
        
        pagination = self.model.query.paginate(
            page=page, 
            per_page=per_page, 
            error_out=False
        )
        
        # Include project_id in list view
        items = [self.serialize(item, include_project_id=True) for item in pagination.items]
        
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
        """Get single site by ID (without project_id in response)."""
        site = self.model.query.get_or_404(resource_id)
        return jsonify(self.serialize(site, include_project_id=False))


# Create CRUD instance
site_crud = SiteCRUD()


@bp.route('/sites', methods=['GET'])
def get_sites():
    """Get paginated list of sites."""
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 50, type=int), 100)
    return site_crud.get_list(page=page, per_page=per_page)


@bp.route('/sites/<int:site_id>', methods=['GET'])
def get_site(site_id):
    """Get single site by ID."""
    return site_crud.get_detail(site_id)


@bp.route('/sites', methods=['POST'])
def create_site():
    """Create a new site."""
    return site_crud.create()


@bp.route('/sites/<int:site_id>', methods=['PUT'])
def update_site(site_id):
    """Update an existing site."""
    return site_crud.update(site_id)


@bp.route('/sites/<int:site_id>', methods=['DELETE'])
def delete_site(site_id):
    """Delete a site."""
    from ..utils import cascade_delete_site
    return site_crud.delete(site_id, cascade_func=cascade_delete_site)