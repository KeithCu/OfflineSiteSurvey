"""Automated tag mapping for CompanyCam integration."""
from difflib import get_close_matches

class TagMapper:
    """Handles automated mapping of app tags to CompanyCam tags."""

    def __init__(self, companycam_service):
        self.companycam_service = companycam_service
        self.companycam_tags = self._load_companycam_tags()

    def _load_companycam_tags(self):
        """Load all tags from CompanyCam."""
        try:
            tags = self.companycam_service.list_tags()
            return tags if tags else []
        except Exception as e:
            # Handle exceptions during tag loading
            return []

    def find_best_match(self, app_tag, cutoff=0.6):
        """
        Find the best match for an app tag from the list of CompanyCam tags.
        """
        if not self.companycam_tags:
            return None

        tag_names = [tag['name'] for tag in self.companycam_tags]
        matches = get_close_matches(app_tag, tag_names, n=1, cutoff=cutoff)

        if matches:
            best_match_name = matches[0]
            for tag in self.companycam_tags:
                if tag['name'] == best_match_name:
                    return tag
        return None
