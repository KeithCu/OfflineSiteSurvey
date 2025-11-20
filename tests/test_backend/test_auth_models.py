import pytest
from backend.models import db
from shared.models import User, Team
from shared.enums import UserRole

def test_user_model_creation(app):
    with app.app_context():
        user = User(
            username="testuser",
            email="test@example.com",
            password_hash="hashedpassword",
            role=UserRole.ADMIN
        )
        db.session.add(user)
        db.session.commit()

        saved_user = User.query.filter_by(username="testuser").first()
        assert saved_user is not None
        assert saved_user.email == "test@example.com"
        assert saved_user.role == UserRole.ADMIN

def test_team_model_creation(app):
    with app.app_context():
        team = Team(name="Test Team")
        db.session.add(team)
        db.session.commit()

        saved_team = Team.query.filter_by(name="Test Team").first()
        assert saved_team is not None

        # Test relationship
        user = User(username="teamuser", email="team@example.com", password_hash="pass", role=UserRole.SURVEYOR)
        user.team = team
        db.session.add(user)
        db.session.commit()

        assert len(saved_team.members) == 1
        assert saved_team.members[0].username == "teamuser"
