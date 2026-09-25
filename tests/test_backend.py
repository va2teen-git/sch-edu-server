import pytest
import json
from app import TaskAttempt, db

def test_login_student(client):
    """Test standard student login."""
    response = client.post('/', data={
        'student_name': 'Тестовый Ученик',
        'grade': '10-tech'
    }, follow_redirects=True)
    
    assert response.status_code == 200
    assert 'Тестовый Ученик'.encode('utf-8') in response.data

def test_login_teacher(client):
    """Test teacher login."""
    response = client.post('/', data={
        'student_name': '#учитель#',
        'grade': 'teacher'
    }, follow_redirects=True)
    
    assert response.status_code == 200
    assert b'DASHBOARD' in response.data

def test_teacher_route_unauthorized(client):
    """Ensure students cannot access the teacher dashboard."""
    client.post('/', data={
        'student_name': 'Тестовый Ученик',
        'grade': '10-tech'
    })
    
    response = client.get('/teacher', follow_redirects=True)
    assert b'DASHBOARD' not in response.data

def test_telemetry_post(client, app):
    """Test telemetry saving in the database."""
    with client.session_transaction() as sess:
        sess['student_name'] = 'Студент Тестер'
        sess['grade'] = '8'

    payload = {
        'mission_name': 'Системы счисления (8 кл) :: Уровень 1',
        'start_time': '2026-09-25T10:00:00.000Z',
        'time_spent_sec': 120,
        'attempts_count': 3,
        'success': True,
        'action_log': '[{"input": "123", "success": true}]',
        'status': 'completed'
    }

    response = client.post('/telemetry', json=payload)
    assert response.status_code == 200

    with app.app_context():
        attempt = TaskAttempt.query.filter_by(student_name='Студент Тестер').first()
        assert attempt is not None
        assert attempt.time_spent_sec == 120
        assert attempt.attempts_count == 3
        assert attempt.success is True

def test_check_parity(client):
    """Test the parity check endpoint logic."""
    with client.session_transaction() as sess:
        sess['student_name'] = 'Студент Тестер'
        sess['m0_has_error'] = False
        sess['m0_task'] = '01100'

    response_no_err = client.post('/check_parity', json={"has_error": False})
    assert response_no_err.status_code == 200
    assert response_no_err.get_json()['success'] is True

    response_err = client.post('/check_parity', json={"has_error": True})
    assert response_err.status_code == 200
    assert response_err.get_json()['success'] is False
