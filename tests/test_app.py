import pytest
import os
import sqlite3

from app import app
from database import DATABASE
from werkzeug.security import generate_password_hash


@pytest.fixture
def client():

    app.config["TESTING"] = True
    app.config["SECRET_KEY"] = "test-secret-key"

    # Create a fresh test database
    if os.path.exists(DATABASE):
        os.remove(DATABASE)

    conn = sqlite3.connect(DATABASE)

    with open("database/schema.sql", "r") as file:
        schema = file.read()

    conn.executescript(schema)

    # Create test users
    users = [
        ("Jashmine", "jashmine@example.com", "1234", "user"),
        ("Support Staff", "support@example.com", "1234", "support"),
        ("Administrator", "admin@example.com", "1234", "admin")
    ]

    for name, email, password, role in users:

        password_hash = generate_password_hash(password)

        conn.execute("""
            INSERT INTO users
            (name, email, password_hash, role)
            VALUES (?, ?, ?, ?)
        """, (
            name,
            email,
            password_hash,
            role
        ))

    conn.commit()
    conn.close()

    with app.test_client() as client:
        yield client

    # Remove test database
    if os.path.exists(DATABASE):
        os.remove(DATABASE)


def login(client, email, password="1234"):

    return client.post(
        "/api/login",
        json={
            "email": email,
            "password": password
        }
    )


def test_home_page(client):

    response = client.get("/")

    assert response.status_code == 200

    assert b"IT Help Desk API is running" in response.data


def test_user_login(client):

    response = login(
        client,
        "jashmine@example.com"
    )

    assert response.status_code == 200

    data = response.get_json()

    assert data["message"] == "Login successful"
    assert data["user"]["role"] == "user"


def test_invalid_login(client):

    response = login(
        client,
        "jashmine@example.com",
        "wrongpassword"
    )

    assert response.status_code == 401


def test_user_can_create_ticket(client):

    login(
        client,
        "jashmine@example.com"
    )

    response = client.post(
        "/api/tickets",
        json={
            "title": "Internet problem",
            "description": "Internet is not working",
            "category": "Network",
            "priority": "High"
        }
    )

    assert response.status_code == 201

    data = response.get_json()

    assert data["message"] == "Ticket created successfully"
    assert "ticket_id" in data


def test_invalid_ticket_category(client):

    login(
        client,
        "jashmine@example.com"
    )

    response = client.post(
        "/api/tickets",
        json={
            "title": "Test ticket",
            "description": "Testing validation",
            "category": "InvalidCategory",
            "priority": "High"
        }
    )

    assert response.status_code == 400


def test_support_cannot_create_ticket(client):

    login(
        client,
        "support@example.com"
    )

    response = client.post(
        "/api/tickets",
        json={
            "title": "Test ticket",
            "description": "Testing role restriction",
            "category": "Network",
            "priority": "Medium"
        }
    )

    assert response.status_code == 403


def test_user_cannot_access_admin_tickets(client):

    login(
        client,
        "jashmine@example.com"
    )

    response = client.get(
        "/api/admin/tickets"
    )

    assert response.status_code == 403


def test_user_can_view_own_tickets(client):

    login(
        client,
        "jashmine@example.com"
    )

    client.post(
        "/api/tickets",
        json={
            "title": "Keyboard problem",
            "description": "Keyboard is not working",
            "category": "Hardware",
            "priority": "Medium"
        }
    )

    response = client.get(
        "/api/my-tickets"
    )

    assert response.status_code == 200

    tickets = response.get_json()

    assert len(tickets) == 1
    assert tickets[0]["title"] == "Keyboard problem"