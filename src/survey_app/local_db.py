import sqlite3
import json
import os
from datetime import datetime
from PIL import Image
import io
import base64

class LocalDatabase:
    def __init__(self, db_path='local_surveys.db'):
        """Initialize the local database"""
        self.db_path = db_path
        self.init_db()

    def init_db(self):
        """Initialize database tables"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Create surveys table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS surveys (
                    id INTEGER PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT,
                    store_name TEXT,
                    store_address TEXT,
                    status TEXT DEFAULT 'draft',
                    data TEXT NOT NULL,
                    last_updated TEXT,
                    synced INTEGER DEFAULT 0
                )
            ''')

            # Create responses table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS responses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    survey_id INTEGER NOT NULL,
                    question TEXT NOT NULL,
                    answer TEXT,
                    response_type TEXT DEFAULT 'text',
                    latitude REAL,
                    longitude REAL,
                    created_at TEXT,
                    synced INTEGER DEFAULT 0,
                    FOREIGN KEY (survey_id) REFERENCES surveys (id)
                )
            ''')

            conn.commit()

    def save_survey(self, survey_data):
        """Save or update a survey locally"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute('''
                INSERT OR REPLACE INTO surveys
                (id, title, description, store_name, store_address, status, data, last_updated, synced)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                survey_data['id'],
                survey_data['title'],
                survey_data.get('description'),
                survey_data.get('store_name'),
                survey_data.get('store_address'),
                survey_data.get('status', 'draft'),
                json.dumps(survey_data),
                datetime.now().isoformat(),
                1  # Mark as synced since we got it from server
            ))

            conn.commit()

    def get_survey(self, survey_id):
        """Get a survey by ID"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT data FROM surveys WHERE id = ?', (survey_id,))
            row = cursor.fetchone()

            if row:
                return json.loads(row[0])
            return None

    def get_surveys(self):
        """Get all surveys"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT data FROM surveys ORDER BY last_updated DESC')
            rows = cursor.fetchall()

            return [json.loads(row[0]) for row in rows]

    def save_responses(self, survey_id, responses):
        """Save responses for a survey"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            for response in responses:
                cursor.execute('''
                    INSERT INTO responses
                    (survey_id, question, answer, response_type, latitude, longitude, created_at, synced)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    survey_id,
                    response['question'],
                    response.get('answer'),
                    response.get('response_type', 'text'),
                    response.get('latitude'),
                    response.get('longitude'),
                    datetime.now().isoformat(),
                    0  # Not synced yet
                ))

            conn.commit()

    def get_responses(self, survey_id):
        """Get all responses for a survey"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT question, answer, response_type, latitude, longitude, created_at
                FROM responses
                WHERE survey_id = ?
                ORDER BY created_at
            ''', (survey_id,))

            rows = cursor.fetchall()
            return [{
                'question': row[0],
                'answer': row[1],
                'response_type': row[2],
                'latitude': row[3],
                'longitude': row[4],
                'created_at': row[5]
            } for row in rows]

    def get_unsynced_responses(self):
        """Get all unsynced responses grouped by survey"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT survey_id, question, answer, response_type, latitude, longitude, created_at
                FROM responses
                WHERE synced = 0
                ORDER BY survey_id, created_at
            ''')

            rows = cursor.fetchall()
            unsynced = {}

            for row in rows:
                survey_id = row[0]
                if survey_id not in unsynced:
                    unsynced[survey_id] = []

                unsynced[survey_id].append({
                    'question': row[1],
                    'answer': row[2],
                    'response_type': row[3],
                    'latitude': row[4],
                    'longitude': row[5],
                    'created_at': row[6]
                })

            return unsynced

    def mark_synced(self, survey_id):
        """Mark all responses for a survey as synced"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE responses SET synced = 1 WHERE survey_id = ?', (survey_id,))
            conn.commit()

    def clear_old_data(self, days=30):
        """Clear old synced data to save space"""
        # This could be implemented to remove old completed surveys
        # For now, we'll keep all data
        pass

    def export_data(self, filename):
        """Export all data to a JSON file"""
        data = {
            'surveys': self.get_surveys(),
            'exported_at': datetime.now().isoformat()
        }

        # Add responses to each survey
        for survey in data['surveys']:
            survey['responses'] = self.get_responses(survey['id'])

        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)

        return filename

    def compress_image(self, image_data, quality=75):
        """Compress image data to specified quality while maintaining dimensions"""
        try:
            # Decode base64 if needed
            if isinstance(image_data, str) and image_data.startswith('data:image'):
                # Handle data URL format
                header, base64_data = image_data.split(',', 1)
                image_bytes = base64.b64decode(base64_data)
            elif isinstance(image_data, str):
                # Assume base64 encoded
                image_bytes = base64.b64decode(image_data)
            else:
                # Assume bytes
                image_bytes = image_data

            # Open image with PIL
            image = Image.open(io.BytesIO(image_bytes))

            # Convert to RGB if necessary (for JPEG compatibility)
            if image.mode in ('RGBA', 'P'):
                image = image.convert('RGB')

            # Compress while maintaining original dimensions
            output_buffer = io.BytesIO()
            image.save(output_buffer, format='JPEG', quality=quality, optimize=True)
            compressed_bytes = output_buffer.getvalue()

            # Return as base64
            return base64.b64encode(compressed_bytes).decode('utf-8')

        except Exception as e:
            print(f"Image compression failed: {e}")
            return image_data  # Return original if compression fails
