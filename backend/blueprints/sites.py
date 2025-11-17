"""Sites blueprint for Flask API."""
from flask import Blueprint, jsonify, request
from ..models import db, Site


bp = Blueprint('sites', __name__, url_prefix='/api')


@bp.route('/sites', methods=['GET'])
def get_sites():
    sites = Site.query.all()
    return jsonify([{
        'id': s.id,
        'name': s.name,
        'address': s.address,
        'latitude': s.latitude,
        'longitude': s.longitude,
        'notes': s.notes,
        'created_at': s.created_at.isoformat(),
        'updated_at': s.updated_at.isoformat()
    } for s in sites])


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
            notes=notes.strip() if notes else None
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
    site = Site.query.get_or_404(site_id)
    db.session.delete(site)
    db.session.commit()
    return jsonify({'message': 'Site deleted successfully'})