import pytest
import time
import threading
from werkzeug.serving import make_server
from playwright.sync_api import Page, expect
from app import db

@pytest.fixture(scope="session")
def test_server():
    from app import app as flask_app
    flask_app.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "WTF_CSRF_ENABLED": False,
    })
    
    with flask_app.app_context():
        db.create_all()

    class ServerThread(threading.Thread):
        def __init__(self, app):
            threading.Thread.__init__(self)
            self.server = make_server('127.0.0.1', 8943, app)
            self.ctx = app.app_context()
            self.ctx.push()

        def run(self):
            self.server.serve_forever()

        def shutdown(self):
            self.server.shutdown()

    server = ServerThread(flask_app)
    server.start()
    time.sleep(1) # wait for server to start
    
    yield "http://127.0.0.1:8943"
    
    server.shutdown()
    server.join()
    with flask_app.app_context():
        db.drop_all()

def test_login_and_navigate(page: Page, test_server):
    """Test full login flow and lesson navigation."""
    page.goto(test_server)
    
    page.fill("input[name='student_name']", "E2E Student")
    page.select_option("select[name='grade']", "10-tech")
    page.click("button[type='submit']")
    
    # We should see the lesson
    page.click("text=Законодательство Российской Федерации")
    
    expect(page.locator("#l1-intro")).to_be_visible()
    expect(page.locator("#l1-workspace")).to_be_hidden()
    
    page.click("#l1-intro button")
    
    expect(page.locator("#l1-intro")).to_be_hidden()
    expect(page.locator("#l1-workspace")).to_be_visible()
    
    time.sleep(1)
    
def test_teacher_dashboard_sees_student(page: Page, test_server):
    """Test that teacher dashboard displays the active student."""
    page.goto(test_server)
    page.fill("input[name='student_name']", "#учитель#")
    page.select_option("select[name='grade']", "10-tech")
    page.click("button[type='submit']")
    
    expect(page.locator("h1")).to_have_text("DASHBOARD")
    expect(page.locator("body")).to_contain_text("E2E Student")
