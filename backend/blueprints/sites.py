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
    data = request.get_json()
    site = Site(
        name=data['name'],
        address=data.get('address'),
        latitude=data.get('latitude'),
        longitude=data.get('longitude'),
        notes=data.get('notes')
    )
    db.session.add(site)
    db.session.commit()
    return jsonify({'id': site.id}), 201


@bp.route('/sites/<int:site_id>', methods=['PUT'])
def update_site(site_id):
    site = Site.query.get_or_404(site_id)
    data = request.get_json()
    site.name = data.get('name', site.name)
    site.address = data.get('address', site.address)
    site.latitude = data.get('latitude', site.latitude)
    site.longitude = data.get('longitude', site.longitude)
    site.notes = data.get('notes', site.notes)
    db.session.commit()
    return jsonify({'message': 'Site updated successfully'})


@bp.route('/sites/<int:site_id>', methods=['DELETE'])
def delete_site(site_id):
    site = Site.query.get_or_404(site_id)
    db.session.delete(site)
    db.session.commit()
    return jsonify({'message': 'Site deleted successfully'})