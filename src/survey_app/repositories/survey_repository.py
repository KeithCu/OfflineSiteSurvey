"""Repository for pure database CRUD operations."""
import json
import logging
from sqlalchemy.orm import Session

from shared.models import (
    Project, Site, Survey, SurveyResponse, SurveyTemplate, TemplateField, Photo
)


class SurveyRepository:
    """Pure database CRUD operations for surveys and related entities."""

    def __init__(self, session_factory):
        """Initialize repository with session factory."""
        self.session_factory = session_factory
        self.logger = logging.getLogger(self.__class__.__name__)

    def _get_session(self):
        """Get a database session."""
        return self.session_factory()

    # Project operations
    def get_projects(self):
        """Get all projects."""
        session = self._get_session()
        try:
            return session.query(Project).all()
        finally:
            session.close()

    def get_project(self, project_id):
        """Get a project by ID."""
        session = self._get_session()
        try:
            return session.get(Project, project_id)
        finally:
            session.close()

    def save_project(self, project_data):
        """Save a project."""
        session = self._get_session()
        try:
            project = Project(**project_data)
            session.add(project)
            session.commit()
            session.refresh(project)
            return project
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def update_project(self, project_id, project_data):
        """Update a project."""
        session = self._get_session()
        try:
            project = session.get(Project, project_id)
            if not project:
                return None
            for key, value in project_data.items():
                setattr(project, key, value)
            session.commit()
            session.refresh(project)
            return project
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def delete_project(self, project_id):
        """Delete a project."""
        session = self._get_session()
        try:
            project = session.get(Project, project_id)
            if project:
                session.delete(project)
                session.commit()
            return project is not None
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    # Site operations
    def get_sites(self):
        """Get all sites."""
        session = self._get_session()
        try:
            return session.query(Site).all()
        finally:
            session.close()

    def get_site(self, site_id):
        """Get a site by ID."""
        session = self._get_session()
        try:
            return session.get(Site, site_id)
        finally:
            session.close()

    def get_sites_for_project(self, project_id):
        """Get sites for a project."""
        session = self._get_session()
        try:
            return session.query(Site).filter_by(project_id=project_id).all()
        finally:
            session.close()

    def save_site(self, site_data):
        """Save a site."""
        session = self._get_session()
        try:
            site = Site(**site_data)
            session.add(site)
            session.commit()
            session.refresh(site)
            return site
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def update_site(self, site_id, site_data):
        """Update a site."""
        session = self._get_session()
        try:
            site = session.get(Site, site_id)
            if not site:
                return None
            for key, value in site_data.items():
                setattr(site, key, value)
            session.commit()
            session.refresh(site)
            return site
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def delete_site(self, site_id):
        """Delete a site."""
        session = self._get_session()
        try:
            site = session.get(Site, site_id)
            if site:
                session.delete(site)
                session.commit()
            return site is not None
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    # Survey operations
    def get_surveys(self):
        """Get all surveys."""
        session = self._get_session()
        try:
            return session.query(Survey).all()
        finally:
            session.close()

    def get_survey(self, survey_id):
        """Get a survey by ID."""
        session = self._get_session()
        try:
            return session.get(Survey, survey_id)
        finally:
            session.close()

    def get_surveys_for_site(self, site_id):
        """Get surveys for a site."""
        session = self._get_session()
        try:
            return session.query(Survey).filter_by(site_id=site_id).all()
        finally:
            session.close()

    def save_survey(self, survey_data):
        """Save a survey."""
        session = self._get_session()
        try:
            survey = Survey(**survey_data)
            session.add(survey)
            session.commit()
            session.refresh(survey)
            return survey
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def update_survey(self, survey_id, survey_data):
        """Update a survey."""
        session = self._get_session()
        try:
            survey = session.get(Survey, survey_id)
            if not survey:
                return None
            for key, value in survey_data.items():
                setattr(survey, key, value)
            session.commit()
            session.refresh(survey)
            return survey
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def delete_survey(self, survey_id):
        """Delete a survey."""
        session = self._get_session()
        try:
            survey = session.get(Survey, survey_id)
            if survey:
                session.delete(survey)
                session.commit()
            return survey is not None
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    # SurveyResponse operations
    def get_responses_for_survey(self, survey_id):
        """Get all responses for a survey."""
        session = self._get_session()
        try:
            return session.query(SurveyResponse).filter_by(survey_id=survey_id).all()
        finally:
            session.close()

    def get_response(self, response_id):
        """Get a response by ID."""
        session = self._get_session()
        try:
            return session.get(SurveyResponse, response_id)
        finally:
            session.close()

    def save_response(self, response_data):
        """Save a response."""
        session = self._get_session()
        try:
            response = SurveyResponse(**response_data)
            session.add(response)
            session.commit()
            session.refresh(response)
            return response
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def save_responses(self, survey_id, responses_dict):
        """Save multiple responses for a survey."""
        session = self._get_session()
        try:
            saved_responses = []
            for question_id, answer in responses_dict.items():
                response_data = {
                    'survey_id': survey_id,
                    'question_id': question_id,
                    'answer': answer
                }
                response = SurveyResponse(**response_data)
                session.add(response)
                saved_responses.append(response)
            session.commit()
            for response in saved_responses:
                session.refresh(response)
            return saved_responses
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def update_response(self, response_id, response_data):
        """Update a response."""
        session = self._get_session()
        try:
            response = session.get(SurveyResponse, response_id)
            if not response:
                return None
            for key, value in response_data.items():
                setattr(response, key, value)
            session.commit()
            session.refresh(response)
            return response
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def delete_response(self, response_id):
        """Delete a response."""
        session = self._get_session()
        try:
            response = session.get(SurveyResponse, response_id)
            if response:
                session.delete(response)
                session.commit()
            return response is not None
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    # Template operations
    def get_templates(self):
        """Get all templates."""
        session = self._get_session()
        try:
            return session.query(SurveyTemplate).all()
        finally:
            session.close()

    def get_template(self, template_id):
        """Get a template by ID."""
        session = self._get_session()
        try:
            return session.get(SurveyTemplate, template_id)
        finally:
            session.close()

    def get_template_fields(self, template_id):
        """Get fields for a template."""
        session = self._get_session()
        try:
            return session.query(TemplateField).filter_by(template_id=template_id).order_by(TemplateField.order_index).all()
        finally:
            session.close()

    def get_conditional_fields(self, template_id):
        """Get conditional fields for a template."""
        session = self._get_session()
        try:
            template = session.get(SurveyTemplate, template_id)
            if not template:
                return {'fields': [], 'section_tags': {}}
            fields = []
            for field in sorted(template.fields, key=lambda x: x.order_index):
                field_data = {
                    'id': field.id, 'field_type': field.field_type, 'question': field.question,
                    'description': field.description, 'required': field.required, 'options': field.options,
                    'order_index': field.order_index, 'section': field.section, 'section_weight': field.section_weight,
                    'conditions': json.loads(field.conditions) if field.conditions else None,
                    'photo_requirements': json.loads(field.photo_requirements) if field.photo_requirements else None
                }
                fields.append(field_data)
            try:
                section_tags = json.loads(template.section_tags) if template.section_tags else {}
            except json.JSONDecodeError:
                section_tags = {}
            return {'fields': fields, 'section_tags': section_tags}
        finally:
            session.close()

    def save_template(self, template_data):
        """Save a template with fields."""
        session = self._get_session()
        try:
            fields = template_data.pop('fields', [])
            section_tags = template_data.pop('section_tags', None)
            template = SurveyTemplate(**template_data)
            if section_tags is not None:
                template.section_tags = json.dumps(section_tags) if isinstance(section_tags, dict) else section_tags
            template = session.merge(template)
            for field_data in fields:
                field = TemplateField(**field_data)
                session.merge(field)
            session.commit()
            session.refresh(template)
            return template
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def update_template_section_tags(self, template_id, section_tags):
        """Update template section tags."""
        session = self._get_session()
        try:
            template = session.get(SurveyTemplate, template_id)
            if not template:
                return False
            template.section_tags = json.dumps(section_tags)
            session.commit()
            return True
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    # Photo operations
    def get_photos(self, survey_id=None, category=None, search_term=None, page=1, per_page=40):
        """Get photos with optional filters."""
        session = self._get_session()
        try:
            query = session.query(Photo)
            if survey_id:
                query = query.filter_by(survey_id=survey_id)
            if category:
                query = query.filter_by(category=category)
            if search_term:
                query = query.filter(Photo.description.contains(search_term))
            total_count = query.count()
            photos = query.order_by(Photo.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()
            
            return {
                'photos': photos,
                'total_count': total_count,
                'page': page,
                'per_page': per_page,
                'total_pages': (total_count + per_page - 1) // per_page
            }
        finally:
            session.close()

    def get_photo(self, photo_id):
        """Get a photo by ID."""
        session = self._get_session()
        try:
            return session.get(Photo, photo_id)
        finally:
            session.close()

    def get_pending_upload_photos(self):
        """Get list of photos that are pending upload."""
        session = self._get_session()
        try:
            return session.query(Photo).filter_by(upload_status='pending').all()
        finally:
            session.close()

    def save_photo(self, photo_data):
        """Save a photo (metadata only, no file I/O)."""
        session = self._get_session()
        try:
            tags = photo_data.get('tags')
            if tags is None:
                tags = []
            if isinstance(tags, (list, tuple)):
                photo_data['tags'] = json.dumps(list(tags))
            elif isinstance(tags, str):
                photo_data['tags'] = tags
            else:
                photo_data['tags'] = json.dumps([])

            if 'corrupted' not in photo_data:
                photo_data['corrupted'] = False

            photo = Photo(**photo_data)
            session.add(photo)
            session.commit()
            session.refresh(photo)
            return photo
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def update_photo(self, photo_id, photo_data):
        """Update a photo."""
        session = self._get_session()
        try:
            photo = session.get(Photo, photo_id)
            if not photo:
                return None
            for key, value in photo_data.items():
                setattr(photo, key, value)
            session.commit()
            session.refresh(photo)
            return photo
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def mark_photo_uploaded(self, photo_id, cloud_url=None, thumbnail_url=None):
        """Mark a photo as uploaded."""
        session = self._get_session()
        try:
            photo = session.get(Photo, photo_id)
            if photo:
                photo.upload_status = 'pending'
                if cloud_url:
                    photo.cloud_url = cloud_url
                if thumbnail_url:
                    photo.thumbnail_url = thumbnail_url
                session.commit()
            return photo
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def mark_requirement_fulfillment(self, photo_id, requirement_id, fulfills=True):
        """Mark photo requirement fulfillment."""
        session = self._get_session()
        try:
            photo = session.get(Photo, photo_id)
            if photo:
                photo.requirement_id = requirement_id
                photo.fulfills_requirement = fulfills
                session.commit()
            return photo
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get_photo_categories(self):
        """Get all unique photo categories."""
        session = self._get_session()
        try:
            categories = session.query(Photo.category).distinct().all()
            return [c[0] for c in categories if c[0]]
        finally:
            session.close()

    def get_all_unique_tags(self):
        """Get all unique tags from photos."""
        session = self._get_session()
        try:
            all_tags = []
            photos = session.query(Photo.tags).filter(Photo.tags.isnot(None)).all()
            unique_tags = set()
            for photo_tags in photos:
                try:
                    tags = json.loads(photo_tags[0])
                    for tag in tags:
                        unique_tags.add(tag)
                except (json.JSONDecodeError, TypeError):
                    continue
            return [{'name': tag} for tag in sorted(list(unique_tags))]
        finally:
            session.close()

    def get_section_for_photo(self, photo_id):
        """Get section name for a photo."""
        session = self._get_session()
        try:
            photo = session.query(Photo).filter_by(id=photo_id).first()
            if not photo or not photo.question_id:
                return None

            field = session.query(TemplateField).filter_by(id=photo.question_id).first()
            if field:
                return field.section
            return None
        finally:
            session.close()

    def get_tags_for_photo(self, photo_id):
        """Get tags for a photo."""
        session = self._get_session()
        try:
            photo = session.query(Photo).filter_by(id=photo_id).first()
            if photo and photo.tags:
                try:
                    return json.loads(photo.tags)
                except (json.JSONDecodeError, TypeError):
                    return []
            return []
        finally:
            session.close()

    # Business logic operations
    def get_survey_progress(self, survey_id):
        """Get survey progress information."""
        session = self._get_session()
        try:
            survey = session.get(Survey, survey_id)
            if not survey:
                return {}
            responses = session.query(SurveyResponse).filter_by(survey_id=survey_id).all()
            response_dict = {r.question_id: r.answer for r in responses if r.question_id}
            photos = session.query(Photo).filter_by(survey_id=survey_id).all()
            fields = []
            if survey.template_id:
                template = session.get(SurveyTemplate, survey.template_id)
                fields = template.fields
            sections = {}
            total_required = 0
            total_completed = 0
            for field in fields:
                section = field.section or 'General'
                if section not in sections:
                    sections[section] = {
                        'required': 0, 'completed': 0, 'photos_required': 0,
                        'photos_taken': 0, 'weight': field.section_weight
                    }
                if field.required:
                    sections[section]['required'] += 1
                    total_required += 1
                    if field.id in response_dict and response_dict[field.id]:
                        sections[section]['completed'] += 1
                        total_completed += 1
                if field.field_type == 'photo':
                    if field.required:
                        sections[section]['photos_required'] += 1
                    photo_exists = any(p for p in photos if p.requirement_id and field.question in p.description)
                    if photo_exists:
                        sections[section]['photos_taken'] += 1
            overall_progress = (total_completed / total_required * 100) if total_required > 0 else 0
            for section_name, section_data in sections.items():
                section_total = section_data['required']
                section_completed = section_data['completed']
                section_data['progress'] = (section_completed / section_total * 100) if section_total > 0 else 0
            return {
                'overall_progress': overall_progress, 'sections': sections,
                'total_required': total_required, 'total_completed': total_completed
            }
        finally:
            session.close()

    def get_photo_requirements(self, survey_id):
        """Get photo requirements for a survey."""
        session = self._get_session()
        try:
            survey = session.get(Survey, survey_id)
            if not survey or not survey.template_id:
                return {}
            template = session.get(SurveyTemplate, survey.template_id)
            photos = session.query(Photo).filter_by(survey_id=survey_id).all()
            existing_photo_requirements = {p.requirement_id: p for p in photos if p.requirement_id}
            requirements_by_section = {}
            for field in sorted(template.fields, key=lambda x: x.order_index):
                if field.field_type == 'photo' and field.photo_requirements:
                    section = field.section or 'General'
                    if section not in requirements_by_section:
                        requirements_by_section[section] = []
                    photo_req_data = json.loads(field.photo_requirements)
                    photo_req_data['field_id'] = field.id
                    photo_req_data['field_question'] = field.question
                    photo_req_data['taken'] = field.id in existing_photo_requirements
                    requirements_by_section[section].append(photo_req_data)
            return {
                'survey_id': survey_id,
                'requirements_by_section': requirements_by_section
            }
        finally:
            session.close()

