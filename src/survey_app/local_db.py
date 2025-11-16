from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, Integer, String, Float, Boolean, Text, LargeBinary, DateTime, ForeignKey
import json
import os
from datetime import datetime
import uuid
import zlib
from appdirs import user_data_dir

Base = declarative_base()

class Site(Base):
    __tablename__ = 'sites'
    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    address = Column(Text)
    latitude = Column(Float)
    longitude = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Survey(Base):
    __tablename__ = 'surveys'
    id = Column(Integer, primary_key=True)
    title = Column(String(200), nullable=False)
    description = Column(Text)
    site_id = Column(Integer, ForeignKey('sites.id'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    status = Column(String(50), default='draft')
    template_id = Column(Integer, ForeignKey('templates.id'))

class SurveyResponse(Base):
    __tablename__ = 'responses'
    id = Column(Integer, primary_key=True)
    survey_id = Column(Integer, ForeignKey('surveys.id'), nullable=False)
    question = Column(String(500), nullable=False)
    answer = Column(Text)
    response_type = Column(String(50))
    latitude = Column(Float)
    longitude = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)

class AppConfig(Base):
    __tablename__ = 'config'
    id = Column(Integer, primary_key=True)
    key = Column(String(100), unique=True, nullable=False)
    value = Column(Text)
    description = Column(String(300))
    category = Column(String(50))
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class SurveyTemplate(Base):
    __tablename__ = 'templates'
    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    category = Column(String(50))
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class TemplateField(Base):
    __tablename__ = 'template_fields'
    id = Column(Integer, primary_key=True)
    template_id = Column(Integer, ForeignKey('templates.id'), nullable=False)
    field_type = Column(String(50))
    question = Column(String(500), nullable=False)
    description = Column(Text)
    required = Column(Boolean, default=False)
    options = Column(Text)
    order_index = Column(Integer, default=0)
    section = Column(String(100))

class Photo(Base):
    __tablename__ = 'photos'
    id = Column(String, primary_key=True)
    survey_id = Column(String, ForeignKey('surveys.id'))
    image_data = Column(LargeBinary)
    latitude = Column(Float)
    longitude = Column(Float)
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    crc = Column(Integer)


class LocalDatabase:
    def __init__(self, db_path='local_surveys.db'):
        """Initialize the local database"""
        self.db_path = db_path
        self.site_id = str(uuid.uuid4())
        self.engine = create_engine(f'sqlite:///{self.db_path}')

        @event.listens_for(self.engine, "connect")
        def load_crsqlite_extension(db_conn, conn_record):
            data_dir = user_data_dir("crsqlite", "vlcn.io")
            lib_path = os.path.join(data_dir, 'crsqlite.so')

            if not os.path.exists(lib_path):
                lib_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'lib', 'crsqlite.so')

            db_conn.enable_load_extension(True)
            db_conn.load_extension(lib_path)

        Base.metadata.create_all(self.engine)

        with self.engine.connect() as connection:
            for table in Base.metadata.sorted_tables:
                connection.execute(text(f"SELECT crsql_as_crr('{table.name}');"))

        self.Session = sessionmaker(bind=self.engine)

    def get_session(self):
        return self.Session()

    def get_surveys(self):
        session = self.get_session()
        surveys = session.query(Survey).all()
        session.close()
        return surveys

    def get_survey(self, survey_id):
        session = self.get_session()
        survey = session.query(Survey).get(survey_id)
        session.close()
        return survey

    def get_sites(self):
        session = self.get_session()
        sites = session.query(Site).all()
        session.close()
        return sites

    def save_site(self, site_data):
        session = self.get_session()
        site = Site(**site_data)
        session.add(site)
        session.commit()
        session.close()

    def get_surveys_for_site(self, site_id):
        session = self.get_session()
        surveys = session.query(Survey).filter_by(site_id=site_id).all()
        session.close()
        return surveys

    def save_survey(self, survey_data):
        session = self.get_session()
        survey = Survey(**survey_data)
        session.add(survey)
        session.commit()
        session.close()

    def get_template_fields(self, template_id):
        session = self.get_session()
        fields = session.query(TemplateField).filter_by(template_id=template_id).all()
        session.close()
        return fields

    def get_templates(self):
        session = self.get_session()
        templates = session.query(SurveyTemplate).all()
        session.close()
        return templates

    def save_template(self, template_data):
        session = self.get_session()
        # a bit of a hack to deal with the fields relationship
        fields = template_data.pop('fields', [])
        template = SurveyTemplate(**template_data)
        session.merge(template)
        for field_data in fields:
            field = TemplateField(**field_data)
            session.merge(field)
        session.commit()
        session.close()

    def save_photo(self, photo_data):
        session = self.get_session()
        photo = Photo(**photo_data)
        session.add(photo)
        session.commit()
        session.close()

    def save_response(self, response_data):
        session = self.get_session()
        response = SurveyResponse(**response_data)
        session.add(response)
        session.commit()
        session.close()

    def get_changes_since(self, version):
        session = self.get_session()
        conn = session.connection()
        # We need the raw connection to get the cursor
        raw_conn = conn.connection
        cursor = raw_conn.cursor()
        cursor.execute(
            "SELECT \"table\", pk, cid, val, col_version, db_version, site_id FROM crsql_changes WHERE db_version > ? AND site_id = ?",
            (version, self.site_id)
        )
        changes = cursor.fetchall()
        # We need to convert the rows to dicts
        changes = [dict(zip([c[0] for c in cursor.description], row)) for row in changes]
        session.close()
        return changes

    def apply_changes(self, changes):
        session = self.get_session()
        conn = session.connection()
        raw_conn = conn.connection
        cursor = raw_conn.cursor()

        for change in changes:
            cursor.execute(
                "INSERT INTO crsql_changes (\"table\", pk, cid, val, col_version, db_version, site_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (change['table'], change['pk'], change['cid'], change['val'], change['col_version'], change['db_version'], change['site_id'])
            )

        session.commit()
        session.close()
