import os
from flask import Flask
from .models import db
from .routes import main
from .companycam_auth import cc_auth
from .tasks import scheduler, init_scheduler
from dotenv import load_dotenv

def create_app():
    load_dotenv() # Load .env file

    app = Flask(__name__)

    # Configuration
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)

    with app.app_context():
        db.create_all()
        # Create a default user for token storage
        from .models import User
        if not User.query.first():
            print("Creating default user...")
            default_user = User(username='admin')
            db.session.add(default_user)
            db.session.commit()

    # Register blueprints
    app.register_blueprint(main)
    app.register_blueprint(cc_auth, url_prefix='/companycam')

    # Initialize and start the scheduler
    init_scheduler(app)

    return app
