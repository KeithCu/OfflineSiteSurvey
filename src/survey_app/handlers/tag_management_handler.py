"""Handler for the Tag Management UI."""
import toga
from toga.style import Pack
from toga.style.pack import COLUMN, ROW

class TagManagementHandler:
    """Handles the logic for the tag management screen."""

    def __init__(self, app):
        self.app = app
        self.window = None

    def show_tag_management_ui(self, widget):
        """Display the tag management window."""
        if not self.app.companycam_service.is_connected():
            self.app.main_window.info_dialog("CompanyCam Not Connected", "Please connect to CompanyCam first.")
            return

        self.window = toga.Window(title="CompanyCam Tag Mapping", size=(600, 400))

        main_box = toga.Box(style=Pack(direction=COLUMN, padding=10))

        # Header
        header = toga.Label("Manage how your app tags map to CompanyCam tags.", style=Pack(font_weight='bold', padding_bottom=10))
        main_box.add(header)

        # Mappings Box
        self.mappings_box = toga.Box(style=Pack(direction=COLUMN, flex=1))

        # Scroll container for mappings
        scroll_container = toga.ScrollContainer(content=self.mappings_box)
        scroll_container.vertical = True

        main_box.add(scroll_container)

        # Buttons
        button_box = toga.Box(style=Pack(direction=ROW, padding_top=10))
        save_button = toga.Button("Save Mappings", on_press=self.save_mappings, style=Pack(padding_right=10))
        close_button = toga.Button("Close", on_press=self.close_window)
        button_box.add(save_button)
        button_box.add(close_button)
        main_box.add(button_box)

        self.window.content = main_box
        self.window.show()

        # Load the tags and build the UI
        self.load_and_display_mappings()

    def load_and_display_mappings(self):
        """Load tags and populate the UI."""
        self.mappings_box.clear()

        # 1. Get all app tags (we'll need a new DB method for this)
        app_tags = self.app.db.get_all_unique_tags() # Assuming this method will be created

        # 2. Get all CompanyCam tags
        companycam_tags = self.app.companycam_service.list_tags()
        if not companycam_tags:
            self.mappings_box.add(toga.Label("Could not load CompanyCam tags."))
            return

        companycam_tag_options = {tag['name']: tag['id'] for tag in companycam_tags}

        # 3. Get saved custom mappings (from config)
        custom_mappings = self.app.config.get('companycam_tag_mappings', {})

        # Create a row for each app tag
        for app_tag in app_tags:
            app_tag_name = app_tag['name']

            # Determine the current mapping
            mapped_id = custom_mappings.get(app_tag_name)
            if not mapped_id:
                # If no custom mapping, find the best automatic match
                best_match = self.app.tag_mapper.find_best_match(app_tag_name)
                if best_match:
                    mapped_id = best_match['id']

            # Create UI components
            label = toga.Label(f"{app_tag_name}:", style=Pack(width=200, padding_right=10))

            # Create a selection dropdown
            dropdown = toga.Selection(items=list(companycam_tag_options.keys()))

            # Set the current value of the dropdown
            if mapped_id:
                for name, id in companycam_tag_options.items():
                    if id == mapped_id:
                        dropdown.value = name
                        break

            row = toga.Box(children=[label, dropdown], style=Pack(direction=ROW, padding_bottom=5))
            self.mappings_box.add(row)


    def save_mappings(self, widget):
        """Save the custom tag mappings."""
        custom_mappings = {}
        companycam_tags = {tag['name']: tag['id'] for tag in self.app.companycam_service.list_tags()}

        for row in self.mappings_box.children:
            app_tag_label = row.children[0]
            companycam_dropdown = row.children[1]

            app_tag_name = app_tag_label.text.replace(':', '').strip()
            selected_cc_tag_name = companycam_dropdown.value

            if selected_cc_tag_name:
                custom_mappings[app_tag_name] = companycam_tags[selected_cc_tag_name]

        self.app.config.set('companycam_tag_mappings', custom_mappings)
        self.app.main_window.info_dialog("Success", "Custom tag mappings have been saved.")
        self.close_window(None)

    def close_window(self, widget):
        """Close the tag management window."""
        if self.window:
            self.window.close()
