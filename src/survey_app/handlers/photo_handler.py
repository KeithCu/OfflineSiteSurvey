"""Photo management handlers for SurveyApp."""
import json
import uuid
import toga
from PIL import Image
import io
import logging
import os
import requests
import hashlib
from shared.enums import PhotoCategory


class PhotoHandler:
    """Handles photo-related operations."""

    def __init__(self, app):
        self.app = app
        self.logger = logging.getLogger(self.__class__.__name__)
        # Config will be set by the app during initialization
        self.config = None

    def show_photos_ui(self, widget):
        """Show photo gallery UI"""
        photos_window = toga.Window(title="Photo Gallery")

        # Search
        self.app.search_input = toga.TextInput(placeholder='Search descriptions', style=toga.Pack(padding=5, flex=1))
        search_button = toga.Button('Search', on_press=lambda w: self.search_photos(photos_window), style=toga.Pack(padding=5))
        search_box = toga.Box(children=[self.app.search_input, search_button], style=toga.Pack(direction=toga.ROW, padding=5))

        # Filter buttons
        filter_label = toga.Label('Filter by Category:', style=toga.Pack(padding=(10, 5, 5, 5)))
        all_button = toga.Button('All', on_press=lambda w: self.filter_photos(photos_window, None), style=toga.Pack(padding=5))
        buttons = [all_button]
        for category in PhotoCategory:
            button = toga.Button(category.value.title(), on_press=lambda w, c=category: self.filter_photos(photos_window, c), style=toga.Pack(padding=5))
            buttons.append(button)

        # Add photo requirements button
        requirements_button = toga.Button('Photo Requirements', on_press=lambda w: self.show_photo_requirements_ui(photos_window), style=toga.Pack(padding=5))
        buttons.append(requirements_button)

        filter_box = toga.Box(
            children=[filter_label] + buttons,
            style=toga.Pack(direction=toga.ROW, padding=5)
        )

        # Photos content
        self.app.photos_scroll_container = toga.ScrollContainer(horizontal=False, vertical=True)
        self.app.current_category = None
        self.app.current_search = None
        self.load_photos_content()  # Load all initially

        close_button = toga.Button('Close', on_press=lambda w: photos_window.close(), style=toga.Pack(padding=10))

        main_photos_box = toga.Box(
            children=[search_box, filter_box, self.app.photos_scroll_container, close_button],
            style=toga.Pack(direction=toga.COLUMN)
        )

        photos_window.content = main_photos_box
        photos_window.show()

    def filter_photos(self, window, category):
        """Filter photos by category"""
        self.app.current_category = category.value if category else None
        self.load_photos_content(page=1)

    def search_photos(self, window):
        """Search photos by description"""
        self.app.current_search = self.app.search_input.value.strip() or None
        self.load_photos_content(page=1)

    def load_photos_content(self, page=1):
        """Load and display photos content with pagination and thumbnails"""
        # STEP 1: Fetch all data first (separate from UI rendering)
        photos_result = self.app.db.get_photos(
            category=self.app.current_category,
            search_term=self.app.current_search,
            page=page,
            per_page=self.config.get('max_visible_photos', 40)
        )

        photos = photos_result['photos']

        if not photos:
            no_photos_label = toga.Label("No photos available", style=toga.Pack(padding=20))
            photos_box = toga.Box(children=[no_photos_label], style=toga.Pack(direction=toga.COLUMN))
            self.app.photos_scroll_container.content = photos_box
            return

        # STEP 2: Prepare all photo data (thumbnails, descriptions, tags) before UI rendering
        photo_data_list = []
        for photo in photos:
            photo_data = {
                'photo': photo,
                'thumb_data': None,
                'description': photo.description or 'No description',
                'tags': []
            }
            
            # Load thumbnail data
            thumb_data = self.app.db.get_photo_data(photo.id, thumbnail=True)
            
            if not thumb_data:
                # Try to load thumbnail from cloud URL
                if photo.thumbnail_url and photo.upload_status == 'completed':
                    try:
                        thumb_data = self._load_image_from_url(photo.thumbnail_url, cache_key=f"{photo.id}_thumb")
                    except Exception as e:
                        self.logger.warning(f"Failed to load thumbnail from {photo.thumbnail_url}: {e}")

            if not thumb_data and photo.cloud_url and photo.upload_status == 'completed':
                # Fallback: load full image from cloud and generate thumbnail
                try:
                    full_image_data = self._load_image_from_url(photo.cloud_url, cache_key=photo.id)
                    if full_image_data:
                        img = Image.open(io.BytesIO(full_image_data))
                        thumb = img.copy()
                        thumb.thumbnail((100, 100))
                        thumb_byte_arr = io.BytesIO()
                        thumb.save(thumb_byte_arr, format='JPEG')
                        thumb_data = thumb_byte_arr.getvalue()
                except Exception as e:
                    self.logger.warning(f"Failed to generate thumbnail from cloud image: {e}")

            if not thumb_data:
                # Try to check if we have full image locally and generate thumbnail on fly
                full_data = self.app.db.get_photo_data(photo.id, thumbnail=False)
                if full_data:
                    try:
                        img = Image.open(io.BytesIO(full_data))
                        thumb = img.copy()
                        thumb.thumbnail((100, 100))
                        thumb_byte_arr = io.BytesIO()
                        thumb.save(thumb_byte_arr, format='JPEG')
                        thumb_data = thumb_byte_arr.getvalue()
                    except Exception as e:
                        self.logger.warning(f"Failed to generate thumbnail from local image: {e}")

            photo_data['thumb_data'] = thumb_data

            # Parse tags
            if getattr(photo, 'tags', None):
                try:
                    photo_data['tags'] = json.loads(photo.tags)
                except (json.JSONDecodeError, TypeError):
                    photo_data['tags'] = []

            photo_data_list.append(photo_data)

        # STEP 3: Now build UI widgets from prepared data
        photos_box = toga.Box(style=toga.Pack(direction=toga.COLUMN, padding=10))

        # Add pagination info
        pagination_label = toga.Label(
            f"Page {photos_result['page']} of {photos_result['total_pages']} ({photos_result['total_count']} total photos)",
            style=toga.Pack(padding=(0, 0, 10, 0), font_size=12)
        )
        photos_box.add(pagination_label)

        # Pagination controls
        pagination_box = toga.Box(style=toga.Pack(direction=toga.ROW, padding=(0, 0, 15, 0)))

        prev_button = toga.Button(
            'Previous',
            on_press=lambda w: self.load_photos_content(max(1, page - 1)),
            style=toga.Pack(padding=5),
            enabled=page > 1
        )

        page_input = toga.TextInput(
            value=str(page),
            style=toga.Pack(width=60, padding=5)
        )

        total_pages_label = toga.Label(
            f" of {photos_result['total_pages']}",
            style=toga.Pack(padding=(5, 0, 5, 0))
        )

        next_button = toga.Button(
            'Next',
            on_press=lambda w: self.load_photos_content(min(photos_result['total_pages'], page + 1)),
            style=toga.Pack(padding=5),
            enabled=page < photos_result['total_pages']
        )

        go_button = toga.Button(
            'Go',
            on_press=lambda w: self.load_photos_content(int(page_input.value) if page_input.value.isdigit() else page),
            style=toga.Pack(padding=5)
        )

        pagination_box.add(prev_button, page_input, total_pages_label, go_button, next_button)
        photos_box.add(pagination_box)

        # Group photos into rows of 4 - now using prepared data
        row_photos = []
        for photo_data in photo_data_list:
            row_photos.append(photo_data)
            if len(row_photos) == 4:
                # Create row
                row_box = toga.Box(style=toga.Pack(direction=toga.ROW, padding=(5, 5, 5, 5)))
                for p_data in row_photos:
                    # Build UI widgets from prepared data
                    if p_data['thumb_data']:
                        image_view = toga.ImageView(data=p_data['thumb_data'], style=toga.Pack(width=100, height=100, padding=5))
                    else:
                        # Placeholder for missing thumbnail
                        image_view = toga.ImageView(style=toga.Pack(width=100, height=100, padding=5, background_color='#cccccc'))

                    desc_label = toga.Label(p_data['description'], style=toga.Pack(text_align='center', font_size=10, padding=(0, 5, 5, 5)))
                    photo_children = [image_view, desc_label]
                    
                    if p_data['tags']:
                        tags_label = toga.Label(f"Tags: {', '.join(p_data['tags'])}", style=toga.Pack(text_align='center', font_size=10, padding=(0, 5, 5, 5), color='#444444'))
                        photo_children.append(tags_label)
                    
                    photo_box = toga.Box(children=photo_children, style=toga.Pack(direction=toga.COLUMN))
                    row_box.add(photo_box)
                photos_box.add(row_box)
                row_photos = []

        # Add remaining photos
        if row_photos:
            row_box = toga.Box(style=toga.Pack(direction=toga.ROW, padding=(5, 5, 5, 5)))
            for p_data in row_photos:
                # Build UI widgets from prepared data
                if p_data['thumb_data']:
                    image_view = toga.ImageView(data=p_data['thumb_data'], style=toga.Pack(width=100, height=100, padding=5))
                else:
                    image_view = toga.ImageView(style=toga.Pack(width=100, height=100, padding=5, background_color='#cccccc'))

                desc_label = toga.Label(p_data['description'], style=toga.Pack(text_align='center', font_size=10, padding=(0, 5, 5, 5)))
                photo_children = [image_view, desc_label]
                
                if p_data['tags']:
                    tags_label = toga.Label(f"Tags: {', '.join(p_data['tags'])}", style=toga.Pack(text_align='center', font_size=10, padding=(0, 5, 5, 5), color='#444444'))
                    photo_children.append(tags_label)
                
                photo_box = toga.Box(children=photo_children, style=toga.Pack(direction=toga.COLUMN))
                row_box.add(photo_box)
            photos_box.add(row_box)

        self.app.photos_scroll_container.content = photos_box

    def _load_image_from_url(self, url, cache_key=None):
        """
        Load image data from URL with local caching.

        Args:
            url: Cloud storage URL
            cache_key: Cache key for local storage (optional)

        Returns:
            bytes: Image data
        """
        # Create cache directory if it doesn't exist
        cache_dir = os.path.join(os.path.dirname(self.app.db.db_path), 'image_cache')
        os.makedirs(cache_dir, exist_ok=True)

        # Generate cache filename
        if cache_key:
            cache_filename = f"{cache_key}.jpg"
        else:
            # Use hash of URL as cache key
            url_hash = hashlib.md5(url.encode()).hexdigest()
            cache_filename = f"{url_hash}.jpg"

        cache_path = os.path.join(cache_dir, cache_filename)

        # Check if cached
        if os.path.exists(cache_path):
            try:
                with open(cache_path, 'rb') as f:
                    return f.read()
            except Exception as e:
                self.logger.warning(f"Failed to read cached image {cache_path}: {e}")

        # Download from URL
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            image_data = response.content

            # Cache locally
            try:
                with open(cache_path, 'wb') as f:
                    f.write(image_data)
            except Exception as e:
                self.logger.warning(f"Failed to cache image {cache_path}: {e}")

            return image_data

        except Exception as e:
            self.logger.error(f"Failed to load image from {url}: {e}")
            raise

    async def take_photo(self, widget):
        """Take a photo using centralized capture"""
        try:
            photo_data = await self.app.capture_photo()
            if photo_data:
                self.app.current_photo_data = photo_data
                self.app.image_view.image = toga.Image(data=self.app.current_photo_data)

                # Get GPS location
                lat, long = self.app.get_gps_location()
                if lat is not None and long is not None:
                    self.app.photo_location_input.value = f"{lat}, {long}"
        except Exception as e:
            self.logger.warning(f"Photo capture failed: {e}")
            if hasattr(self.app, 'status_label'):
                self.app.status_label.text = "Photo capture failed."

    def save_photo(self, widget):
        """Save photo (legacy method)"""
        if self.app.current_survey and hasattr(self.app, 'current_photo_data'):
            latitude, longitude = None, None
            try:
                lat_str, lon_str = self.app.photo_location_input.value.split(',')
                latitude = float(lat_str.strip())
                longitude = float(lon_str.strip())
            except (ValueError, IndexError):
                pass  # Ignore if location is not a valid lat,long pair

            photo_data = {
                'id': str(uuid.uuid4()),
                'survey_id': self.app.current_survey['id'],
                'image_data': self.app.current_photo_data,
                'latitude': latitude,
                'longitude': longitude,
                'description': self.app.photo_description_input.value,
                'tags': list(self.app.selected_photo_tags)
            }
            self.app.db.save_photo(photo_data)
            self.app.status_label.text = "Photo saved locally"
            self.app.clear_photo_tag_selection()
            
            # Also persist last_photo_id for requirement tracking
            self.app.last_photo_id = photo_data['id']
        else:
            self.app.status_label.text = "Please select a survey and take a photo first"

    def show_photo_requirements_ui(self, parent_window):
        """Show photo requirements checklist UI"""
        if not self.app.current_survey:
            self.app.status_label.text = "Please select a survey first"
            return
        
        requirements_window = toga.Window(title="Photo Requirements")

        # Get photo requirements
        requirements_data = self.app.db.get_photo_requirements(self.app.current_survey['id'])
        requirements_by_section = requirements_data.get('requirements_by_section', {})

        # Create requirements content
        requirements_box = toga.Box(style=toga.Pack(direction=toga.COLUMN, padding=10))

        if not requirements_by_section:
            no_requirements_label = toga.Label("No photo requirements for this survey", style=toga.Pack(padding=20))
            requirements_box.add(no_requirements_label)
        else:
            for section_name, section_requirements in requirements_by_section.items():
                # Section header
                section_label = toga.Label(
                    f"{section_name} Section",
                    style=toga.Pack(font_size=16, font_weight='bold', padding=(10, 5, 5, 5))
                )
                requirements_box.add(section_label)

                # Requirements list
                for req in section_requirements:
                    req_item = self.create_requirement_item(req)
                    requirements_box.add(req_item)

        close_button = toga.Button('Close', on_press=lambda w: requirements_window.close(), style=toga.Pack(padding=10))
        requirements_box.add(close_button)

        requirements_window.content = requirements_box
        requirements_window.show()

    def create_requirement_item(self, requirement):
        """Create UI item for a photo requirement"""
        req_box = toga.Box(style=toga.Pack(direction=toga.ROW, padding=5))

        # Status indicator
        status_color = 'red' if requirement.get('required', False) else 'gray'
        if requirement.get('taken', False):
            status_color = 'green'

        status_indicator = toga.Label(
            '●',
            style=toga.Pack(color=status_color, padding=(0, 5, 0, 0))
        )

        # Requirement text
        req_text = requirement.get('title', 'Photo requirement')
        if requirement.get('required', False):
            req_text += " (Required)"
        else:
            req_text += " (Optional)"

        req_label = toga.Label(req_text, style=toga.Pack(flex=1))

        # Take photo button
        take_photo_btn = toga.Button(
            '📷',
            on_press=lambda w, req_id=requirement.get('field_id'): self.take_requirement_photo(req_id),
            style=toga.Pack(padding=(0, 0, 0, 5))
        )

        req_box.add(status_indicator, req_label, take_photo_btn)
        return req_box

    async def take_requirement_photo(self, field_id):
        """Take a photo for a specific requirement"""
        # Find the field for this requirement
        field = next((f for f in self.app.template_fields if f['id'] == field_id), None)
        if not field:
            self.app.status_label.text = "Requirement not found"
            return

        # Use existing photo capture logic
        await self.app.survey_handler.take_photo_enhanced(None)

        # Mark photo as fulfilling requirement
        if hasattr(self.app, 'last_photo_id'):
            self.app.db.mark_requirement_fulfillment(self.app.last_photo_id, field_id, True)
            self.app.status_label.text = f"Photo captured for requirement: {field['question']}"
