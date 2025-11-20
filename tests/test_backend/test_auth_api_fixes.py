import pytest
from shared.models import User, Team, UserRole
from backend.models import db, AppConfig

def test_initial_api_key_generation(client, app):
    """Test that /api/auth/key is accessible without auth for initial setup."""
    # Ensure no users or keys exist (should be true in fresh test db)
    with app.app_context():
        assert User.query.count() == 0
        assert AppConfig.query.filter_by(category='auth').count() == 0

    response = client.post('/api/auth/key')
    assert response.status_code == 200
    assert 'api_key' in response.get_json()

def test_manager_team_permission(client, app):
    """Test that managers can only add members to their own team."""
    with app.app_context():
        # Create teams
        team1 = Team(name="Team 1")
        team2 = Team(name="Team 2")
        db.session.add(team1)
        db.session.add(team2)
        db.session.commit()

        # Create manager
        manager = User(
            username="manager1",
            email="manager1@example.com",
            password_hash="hash",
            role=UserRole.MANAGER,
            team_id=team1.id
        )
        db.session.add(manager)

        # Create user to add
        user_to_add = User(
            username="newuser",
            email="newuser@example.com",
            password_hash="hash",
            role=UserRole.SURVEYOR
        )
        db.session.add(user_to_add)
        db.session.commit()

        manager_id = manager.id
        team1_id = team1.id
        team2_id = team2.id

        # Generate token for manager (manually as login is complex/hashed)
        token = "test_token_manager"
        config = AppConfig(
            key=f'token_{token}',
            value=str(manager.id),
            category='user_token'
        )
        db.session.add(config)
        db.session.commit()

    # Try to add user to Team 1 (Own Team) - Should succeed
    response = client.post(
        f'/api/teams/{team1_id}/members',
        json={'username': 'newuser'},
        headers={'Authorization': f'Bearer {token}'}
    )
    assert response.status_code == 200

    # Try to add user to Team 2 (Other Team) - Should fail
    response = client.post(
        f'/api/teams/{team2_id}/members',
        json={'username': 'newuser'},
        headers={'Authorization': f'Bearer {token}'}
    )
    assert response.status_code == 403
