"""Image service for file I/O and image processing."""
import os
import logging
import secrets
import uuid

from shared.utils import compute_photo_hash, generate_thumbnail, CorruptedImageError


class ImageService:
    """Service for handling photo file I/O and image processing."""

    def __init__(self, photos_dir):
        """Initialize image service with photos directory."""
        self.photos_dir = photos_dir
        self.logger = logging.getLogger(self.__class__.__name__)
        os.makedirs(self.photos_dir, exist_ok=True)
        self.logger.info(f"Image service initialized with photos directory: {self.photos_dir}")

    def save_photo_file(self, photo_id, image_data, thumbnail_data=None):
        """Save photo data to local filesystem."""
        try:
            photo_filename = f"{photo_id}.jpg"
            photo_path = os.path.join(self.photos_dir, photo_filename)
            
            with open(photo_path, 'wb') as f:
                f.write(image_data)
            
            if thumbnail_data:
                thumb_filename = f"{photo_id}_thumb.jpg"
                thumb_path = os.path.join(self.photos_dir, thumb_filename)
                with open(thumb_path, 'wb') as f:
                    f.write(thumbnail_data)
                    
            return photo_filename
        except Exception as e:
            self.logger.error(f"Failed to save local photo file for {photo_id}: {e}")
            raise

    def get_photo_data(self, photo_id, thumbnail=False):
        """Retrieve photo data from local filesystem."""
        try:
            filename = f"{photo_id}_thumb.jpg" if thumbnail else f"{photo_id}.jpg"
            photo_path = os.path.join(self.photos_dir, filename)
            
            if os.path.exists(photo_path):
                with open(photo_path, 'rb') as f:
                    return f.read()
            return None
        except Exception as e:
            self.logger.error(f"Failed to read local photo file for {photo_id}: {e}")
            return None

    def get_photo_path(self, photo_id):
        """Get absolute path to local photo file."""
        photo_path = os.path.join(self.photos_dir, f"{photo_id}.jpg")
        if os.path.exists(photo_path):
            return photo_path
        return None

    def process_photo(self, image_data, photo_id=None, survey_id=None, site_id=None, section='general'):
        """Process photo: generate hash, thumbnail, and prepare metadata."""
        if not photo_id:
            photo_id = self._generate_photo_id(survey_id, site_id, section)

        photo_hash = compute_photo_hash(image_data)
        size_bytes = len(image_data)
        
        thumbnail_data = None
        corrupted = False
        try:
            thumbnail_data = generate_thumbnail(image_data, max_size=200)
        except CorruptedImageError as e:
            self.logger.error(f"Corrupted image detected for photo {photo_id}: {e}")
            corrupted = True

        return {
            'id': photo_id,
            'hash_value': photo_hash,
            'size_bytes': size_bytes,
            'thumbnail_data': thumbnail_data,
            'corrupted': corrupted
        }

    def _generate_photo_id(self, survey_id=None, site_id=None, section='general'):
        """Generate a photo ID."""
        if site_id:
            section_name = section.lower().replace(" ", "_")
            random_string = secrets.token_hex(4)
            return f"{site_id}-{section_name}-{random_string}"
        return str(uuid.uuid4())

