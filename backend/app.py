from flask import Flask, jsonify, request, g
import sqlite3
import json
import datetime
import enum
import os
from appdirs import user_data_dir
from store_survey_template import STORE_SURVEY_TEMPLATE
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import event, text
from sqlalchemy.engine import Engine
import click

app = Flask(__name__)

DB_NAME = 'backend_main.db'
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DB_NAME}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Load the cr-sqlite extension
def load_crsqlite_extension(db_conn, conn_record):
    # Look for the library in the user data directory
    data_dir = user_data_dir("crsqlite", "vlcn.io")
    lib_path = os.path.join(data_dir, 'crsqlite.so')

    if not os.path.exists(lib_path):
        # As a fallback for development, check the project's lib directory
        lib_path = os.path.join(os.path.dirname(__file__), 'lib', 'crsqlite.so')

    db_conn.enable_load_extension(True)
    db_conn.load_extension(lib_path)

event.listen(Engine, "connect", load_crsqlite_extension)


class SurveyStatus(enum.Enum):
    DRAFT = 'draft'
    ACTIVE = 'active'
    COMPLETED = 'completed'
    ARCHIVED = 'archived'

class Survey(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    store_name = db.Column(db.String(100))
    store_address = db.Column(db.String(300))
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    status = db.Column(db.Enum(SurveyStatus), default=SurveyStatus.DRAFT)
    responses = db.relationship('SurveyResponse', backref='survey', lazy=True)
    template_id = db.Column(db.Integer, db.ForeignKey('survey_template.id'))

class SurveyResponse(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    survey_id = db.Column(db.Integer, db.ForeignKey('survey.id'), nullable=False)
    question = db.Column(db.String(500), nullable=False)
    answer = db.Column(db.Text)
    response_type = db.Column(db.String(50))
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

class AppConfig(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.Text)
    description = db.Column(db.String(300))
    category = db.Column(db.String(50))
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

class SurveyTemplate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    category = db.Column(db.String(50))
    is_default = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    fields = db.relationship('TemplateField', backref='template', lazy=True, cascade='all, delete-orphan')

class TemplateField(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    template_id = db.Column(db.Integer, db.ForeignKey('survey_template.id'), nullable=False)
    field_type = db.Column(db.String(50))
    question = db.Column(db.String(500), nullable=False)
    description = db.Column(db.Text)
    required = db.Column(db.Boolean, default=False)
    options = db.Column(db.Text)
    order_index = db.Column(db.Integer, default=0)
    section = db.Column(db.String(100))

class Photo(db.Model):
    id = db.Column(db.String, primary_key=True)
    survey_id = db.Column(db.String, db.ForeignKey('survey.id'))
    image_data = db.Column(db.LargeBinary)
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    crc = db.Column(db.Integer)


def create_crr_tables(target, connection, **kw):
    connection.execute(text("SELECT crsql_as_crr('survey');"))
    connection.execute(text("SELECT crsql_as_crr('survey_response');"))
    connection.execute(text("SELECT crsql_as_crr('app_config');"))
    connection.execute(text("SELECT crsql_as_crr('survey_template');"))
    connection.execute(text("SELECT crsql_as_crr('template_field');"))
    connection.execute(text("SELECT crsql_as_crr('photo');"))

event.listen(db.metadata, 'after_create', create_crr_tables)

@app.cli.command('init-db')
def init_db_command():
    """Clear the existing data and create new tables."""
    with app.app_context():
        db.create_all()

        # Seed initial data
        if not AppConfig.query.filter_by(key='image_compression_quality').first():
            config = AppConfig(key='image_compression_quality', value='75')
            db.session.add(config)

        if not SurveyTemplate.query.filter_by(is_default=True).first():
            template = SurveyTemplate(name=STORE_SURVEY_TEMPLATE['name'], description=STORE_SURVEY_TEMPLATE['description'], category=STORE_SURVEY_TEMPLATE['category'], is_default=True)
            db.session.add(template)
            db.session.flush()
            for field_data in STORE_SURVEY_TEMPLATE['fields']:
                field = TemplateField(template_id=template.id, **field_data)
                db.session.add(field)

        db.session.commit()
    click.echo('Initialized the database.')

@app.route('/api/surveys', methods=['GET'])
def get_surveys():
    surveys = Survey.query.all()
    return jsonify([{'id': s.id, 'title': s.title} for s in surveys])

@app.route('/api/surveys/<int:survey_id>', methods=['GET'])
def get_survey(survey_id):
    survey = Survey.query.get_or_404(survey_id)
    return jsonify({'id': survey.id, 'title': survey.title, 'responses': [{'id': r.id, 'question': r.question} for r in survey.responses]})

@app.route('/api/surveys', methods=['POST'])
def create_survey():
    data = request.get_json()
    survey = Survey(title=data['title'], template_id=data.get('template_id'))
    db.session.add(survey)
    db.session.commit()
    return jsonify({'id': survey.id}), 201

@app.route('/api/templates', methods=['GET'])
def get_templates():
    templates = SurveyTemplate.query.all()
    return jsonify([{'id': t.id, 'name': t.name, 'fields': [{'id': f.id, 'question': f.question} for f in t.fields]} for t in templates])

@app.route('/api/changes', methods=['POST'])
def apply_changes():
    changes = request.get_json()
    conn = db.engine.raw_connection()
    cursor = conn.cursor()

    for change in changes:
        cursor.execute(
            "INSERT INTO crsql_changes (\"table\", pk, cid, val, col_version, db_version, site_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (change['table'], change['pk'], change['cid'], change['val'], change['col_version'], change['db_version'], change['site_id'])
        )

    conn.commit()
    conn.close()

    return jsonify({'message': 'Changes applied successfully'})

@app.route('/api/changes', methods=['GET'])
def get_changes():
    version = request.args.get('version', 0)
    site_id = request.args.get('site_id')

    conn = db.engine.raw_connection()
    cursor = conn.cursor()
    cursor.row_factory = sqlite3.Row

    cursor.execute(
        "SELECT \"table\", pk, cid, val, col_version, db_version, site_id FROM crsql_changes WHERE db_version > ? AND site_id != ?",
        (version, site_id)
    )

    changes = cursor.fetchall()
    conn.close()

    return jsonify([dict(row) for row in changes])

if __name__ == '__main__':
    app.run(debug=True)
