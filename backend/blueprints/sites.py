"""Sites blueprint for Flask API."""
from flask import Blueprint, jsonify, request
from ..models import db, Site


bp = Blueprint('sites', __name__, url_prefix='/api')


@bp.route('/sites', methods=['GET'])
def get_sites():
    # Pagination parameters
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 50, type=int), 100)  # Max 100 per page

    # Query with pagination
    pagination = Site.query.paginate(page=page, per_page=per_page, error_out=False)
    sites = pagination.items

    return jsonify({
        'sites': [{
            'id': s.id,
            'name': s.name,
            'address': s.address,
            'latitude': s.latitude,
            'longitude': s.longitude,
            'notes': s.notes,
            'project_id': s.project_id,
            'created_at': s.created_at.isoformat(),
            'updated_at': s.updated_at.isoformat()
        } for s in sites],
        'pagination': {
            'page': pagination.page,
            'per_page': pagination.per_page,
            'total': pagination.total,
            'pages': pagination.pages,
            'has_next': pagination.has_next,
            'has_prev': pagination.has_prev
        }
    })


@bp.route('/sites/<int:site_id>', methods=['GET'])
def get_site(site_id):
    site = Site.query.get_or_404(site_id)
    return jsonify({
        'id': site.id,
        'name': site.name,
        'address': site.address,
        'latitude': site.latitude,
        'longitude': site.longitude,
        'notes': site.notes,
        'created_at': site.created_at.isoformat(),
        'updated_at': site.updated_at.isoformat()
    })


@bp.route('/sites', methods=['POST'])
def create_site():
    try:
        data = request.get_json()
    except Exception:
        return jsonify({'error': 'Invalid JSON data'}), 400

    if not isinstance(data, dict):
        return jsonify({'error': 'Request data must be a JSON object'}), 400

    # Validate required fields
    if 'name' not in data:
        return jsonify({'error': 'name field is required'}), 400

    name = data['name']
    if not isinstance(name, str) or not name.strip():
        return jsonify({'error': 'name must be a non-empty string'}), 400

    # Validate optional fields
    address = data.get('address')
    if address is not None and not isinstance(address, str):
        return jsonify({'error': 'address must be a string'}), 400

    # Validate project_id exists
    project_id = data.get('project_id')
    if project_id is not None:
        try:
            project_id = int(project_id)
        except (ValueError, TypeError):
            return jsonify({'error': 'project_id must be an integer'}), 400

        from ..utils import validate_foreign_key
        if not validate_foreign_key('projects', 'id', project_id):
            return jsonify({'error': f'project_id {project_id} does not exist'}), 400
    else:
        return jsonify({'error': 'project_id is required'}), 400

    latitude = data.get('latitude')
    if latitude is not None:
        try:
            latitude = float(latitude)
            if not (-90 <= latitude <= 90):
                return jsonify({'error': 'latitude must be between -90 and 90'}), 400
        except (ValueError, TypeError):
            return jsonify({'error': 'latitude must be a number'}), 400

    longitude = data.get('longitude')
    if longitude is not None:
        try:
            longitude = float(longitude)
            if not (-180 <= longitude <= 180):
                return jsonify({'error': 'longitude must be between -180 and 180'}), 400
        except (ValueError, TypeError):
            return jsonify({'error': 'longitude must be a number'}), 400

    notes = data.get('notes')
    if notes is not None and not isinstance(notes, str):
        return jsonify({'error': 'notes must be a string'}), 400

    try:
        site = Site(
            name=name.strip(),
            address=address.strip() if address else None,
            latitude=latitude,
            longitude=longitude,
            notes=notes.strip() if notes else None,
            project_id=project_id
        )
        db.session.add(site)
        db.session.commit()
        return jsonify({'id': site.id}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to create site: {str(e)}'}), 500


@bp.route('/sites/<int:site_id>', methods=['PUT'])
def update_site(site_id):
    try:
        data = request.get_json()
    except Exception:
        return jsonify({'error': 'Invalid JSON data'}), 400

    if not isinstance(data, dict):
        return jsonify({'error': 'Request data must be a JSON object'}), 400

    site = Site.query.get_or_404(site_id)

    # Validate and update name
    if 'name' in data:
        name = data['name']
        if not isinstance(name, str) or not name.strip():
            return jsonify({'error': 'name must be a non-empty string'}), 400
        site.name = name.strip()

    # Validate and update project_id
    if 'project_id' in data:
        project_id = data['project_id']
        if project_id is not None:
            try:
                project_id = int(project_id)
            except (ValueError, TypeError):
                return jsonify({'error': 'project_id must be an integer'}), 400

            from ..utils import validate_foreign_key
            if not validate_foreign_key('projects', 'id', project_id):
                return jsonify({'error': f'project_id {project_id} does not exist'}), 400
        site.project_id = project_id

    # Validate and update address
    if 'address' in data:
        address = data['address']
        if address is not None and not isinstance(address, str):
            return jsonify({'error': 'address must be a string'}), 400
        site.address = address.strip() if address else None

    # Validate and update latitude
    if 'latitude' in data:
        latitude = data['latitude']
        if latitude is not None:
            try:
                latitude = float(latitude)
                if not (-90 <= latitude <= 90):
                    return jsonify({'error': 'latitude must be between -90 and 90'}), 400
            except (ValueError, TypeError):
                return jsonify({'error': 'latitude must be a number'}), 400
        site.latitude = latitude

    # Validate and update longitude
    if 'longitude' in data:
        longitude = data['longitude']
        if longitude is not None:
            try:
                longitude = float(longitude)
                if not (-180 <= longitude <= 180):
                    return jsonify({'error': 'longitude must be between -180 and 180'}), 400
            except (ValueError, TypeError):
                return jsonify({'error': 'longitude must be a number'}), 400
        site.longitude = longitude

    # Validate and update notes
    if 'notes' in data:
        notes = data['notes']
        if notes is not None and not isinstance(notes, str):
            return jsonify({'error': 'notes must be a string'}), 400
        site.notes = notes.strip() if notes else None

    try:
        db.session.commit()
        return jsonify({'message': 'Site updated successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to update site: {str(e)}'}), 500


@bp.route('/sites/<int:site_id>', methods=['DELETE'])
def delete_site(site_id):
    from ..utils import cascade_delete_site

    try:
        summary = cascade_delete_site(site_id)
        db.session.commit()

        return jsonify({
            'message': 'Site deleted successfully',
            'summary': summary
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to delete site: {str(e)}'}), 500