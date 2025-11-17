"""Database service wrapper for LocalDatabase methods."""


class DBService:
    """Wrapper for LocalDatabase operations."""

    def __init__(self, db):
        self.db = db

    def get_projects(self):
        """Get all projects."""
        return self.db.get_projects()

    def get_sites(self):
        """Get all sites."""
        return self.db.get_sites()

    def get_sites_for_project(self, project_id):
        """Get sites for a project."""
        return self.db.get_sites_for_project(project_id)

    def get_surveys_for_site(self, site_id):
        """Get surveys for a site."""
        return self.db.get_surveys_for_site(site_id)

    def get_templates(self):
        """Get all templates."""
        return self.db.get_templates()

    def get_template_fields(self, template_id):
        """Get fields for a template."""
        return self.db.get_template_fields(template_id)

    def get_photos(self, **kwargs):
        """Get photos with filters."""
        return self.db.get_photos(**kwargs)

    def get_survey_progress(self, survey_id):
        """Get survey progress."""
        return self.db.get_survey_progress(survey_id)

    def get_photo_requirements(self, survey_id):
        """Get photo requirements for survey."""
        return self.db.get_photo_requirements(survey_id)

    def save_project(self, project_data):
        """Save a project."""
        return self.db.save_project(project_data)

    def save_site(self, site_data):
        """Save a site."""
        return self.db.save_site(site_data)

    def save_survey(self, survey_data):
        """Save a survey."""
        return self.db.save_survey(survey_data)

    def save_response(self, response_data):
        """Save a response."""
        return self.db.save_response(response_data)

    def save_photo(self, photo_data):
        """Save a photo."""
        return self.db.save_photo(photo_data)

    def get_changes_since(self, version):
        """Get changes since version."""
        return self.db.get_changes_since(version)

    def get_current_version(self):
        """Get current CRDT version."""
        return self.db.get_current_version()

    def apply_changes(self, changes):
        """Apply CRDT changes."""
        return self.db.apply_changes(changes)

    def should_show_field(self, conditions, responses):
        """Check if field should be shown."""
        return self.db.should_show_field(conditions, responses)

    def mark_requirement_fulfillment(self, photo_id, requirement_id, fulfills=True):
        """Mark photo requirement fulfillment."""
        return self.db.mark_requirement_fulfillment(photo_id, requirement_id, fulfills)