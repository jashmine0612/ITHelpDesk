from flask import Flask, request, jsonify, session, render_template
from werkzeug.security import check_password_hash
from database import get_db_connection

app = Flask(__name__)

import os

app.secret_key = os.environ.get(
    "SECRET_KEY",
    "development-secret-key"
)


@app.route("/")
def home():
    return "IT Help Desk API is running"

@app.route("/register")
def register_page():
    return render_template("register.html")


@app.route("/api/register", methods=["POST"])
def register():
    data = request.get_json()

    if not data:
        return jsonify({"error": "Request data is required"}), 400

    name = data.get("name", "").strip()
    email = data.get("email", "").strip()
    password = data.get("password", "")

    if not name or not email or not password:
        return jsonify({
            "error": "Name, email and password are required"
        }), 400

    if len(password) < 4:
        return jsonify({
            "error": "Password must be at least 4 characters"
        }), 400

    conn = get_db_connection()

    existing_user = conn.execute("""
        SELECT id
        FROM users
        WHERE email = ?
    """, (email,)).fetchone()

    if existing_user:
        conn.close()
        return jsonify({
            "error": "An account with this email already exists"
        }), 409

    from werkzeug.security import generate_password_hash

    password_hash = generate_password_hash(password)

    conn.execute("""
        INSERT INTO users
        (name, email, password_hash, role)
        VALUES (?, ?, ?, 'user')
    """, (
        name,
        email,
        password_hash
    ))

    conn.commit()
    conn.close()

    return jsonify({
        "message": "Registration successful"
    }), 201
@app.route("/login")
def login_page():
    return render_template("login.html")
@app.route("/create-ticket")
def create_ticket_page():
    if "user_id" not in session:
        return render_template("login.html")

    if session["role"] != "user":
        return "Access denied", 403

    return render_template("create_ticket.html")
# Create a ticket
@app.route("/user-dashboard")
def user_dashboard():

    if "user_id" not in session:
        return render_template("login.html")

    if session["role"] != "user":
        return "Access denied", 403

    return render_template("user_dashboard.html")


@app.route("/support-dashboard")
def support_dashboard():

    if "user_id" not in session:
        return render_template("login.html")

    if session["role"] != "support":
        return "Access denied", 403

    return render_template("support_dashboard.html")


@app.route("/admin-dashboard")
def admin_dashboard():

    if "user_id" not in session:
        return render_template("login.html")

    if session["role"] != "admin":
        return "Access denied", 403

    return render_template("admin_dashboard.html")
@app.route("/api/my-tickets", methods=["GET"])
def my_tickets():

    if "user_id" not in session:
        return jsonify({"error": "Login required"}), 401

    conn = get_db_connection()

    tickets = conn.execute("""
        SELECT
            id,
            title,
            description,
            category,
            priority,
            status,
            resolution,
            created_at,
            due_at
        FROM tickets
        WHERE user_id = ?
        ORDER BY created_at DESC
    """, (session["user_id"],)).fetchall()

    conn.close()

    return jsonify([dict(ticket) for ticket in tickets])
@app.route("/api/assigned-tickets", methods=["GET"])
def assigned_tickets():

    if "user_id" not in session:
        return jsonify({"error": "Login required"}), 401

    if session["role"] != "support":
        return jsonify({"error": "Access denied"}), 403

    conn = get_db_connection()

    tickets = conn.execute("""
        SELECT
            id,
            title,
            description,
            category,
            priority,
            status,
            resolution,
            created_at,
            due_at
        FROM tickets
        WHERE assigned_to = ?
        ORDER BY created_at DESC
    """, (session["user_id"],)).fetchall()

    conn.close()

    return jsonify([dict(ticket) for ticket in tickets])
@app.route("/api/admin/tickets", methods=["GET"])
def admin_tickets():
    if "user_id" not in session:
        return jsonify({"error": "Login required"}), 401

    if session["role"] != "admin":
        return jsonify({"error": "Access denied"}), 403

    search = request.args.get("search", "").strip()
    category = request.args.get("category", "").strip()
    priority = request.args.get("priority", "").strip()
    status = request.args.get("status", "").strip()

    query = """
        SELECT
            tickets.id,
            tickets.title,
            tickets.category,
            tickets.priority,
            tickets.status,
            tickets.created_at,
            users.name AS assigned_name
        FROM tickets
        LEFT JOIN users
            ON tickets.assigned_to = users.id
        WHERE 1=1
    """

    params = []

    if search:
        query += " AND tickets.title LIKE ?"
        params.append(f"%{search}%")

    if category:
        query += " AND tickets.category = ?"
        params.append(category)

    if priority:
        query += " AND tickets.priority = ?"
        params.append(priority)

    if status:
        query += " AND tickets.status = ?"
        params.append(status)

    query += " ORDER BY tickets.created_at DESC"

    conn = get_db_connection()

    tickets = conn.execute(query, params).fetchall()

    conn.close()

    return jsonify([dict(ticket) for ticket in tickets])
@app.route("/support-ticket/<int:ticket_id>")
def support_ticket_page(ticket_id):

    if "user_id" not in session:
        return render_template("login.html")

    if session["role"] != "support":
        return "Access denied", 403

    return render_template(
        "support_ticket.html",
        ticket_id=ticket_id
    )      
@app.route("/api/tickets", methods=["POST"])
def create_ticket():
    if "user_id" not in session:
        return jsonify({"error": "Login required"}), 401

    if session["role"] != "user":
        return jsonify({"error": "Only users can create tickets"}), 403

    data = request.get_json()

    if not data:
        return jsonify({"error": "Request data is required"}), 400

    title = data.get("title", "").strip()
    description = data.get("description", "").strip()
    category = data.get("category", "").strip()
    priority = data.get("priority", "Medium").strip()

    allowed_categories = [
        "Hardware",
        "Software",
        "Network",
        "Account",
        "Other"
    ]

    allowed_priorities = [
        "Low",
        "Medium",
        "High",
        "Critical"
    ]

    if not title:
        return jsonify({"error": "Title is required"}), 400

    if not description:
        return jsonify({"error": "Description is required"}), 400

    if category not in allowed_categories:
        return jsonify({"error": "Invalid category"}), 400

    if priority not in allowed_priorities:
        return jsonify({"error": "Invalid priority"}), 400

    if len(title) > 100:
        return jsonify({"error": "Title must be 100 characters or less"}), 400

    conn = get_db_connection()

    cursor = conn.execute("""
        INSERT INTO tickets
        (user_id, title, description, category, priority)
        VALUES (?, ?, ?, ?, ?)
    """, (
        session["user_id"],
        title,
        description,
        category,
        priority
    ))

    ticket_id = cursor.lastrowid

    conn.commit()
    conn.close()

    return jsonify({
        "message": "Ticket created successfully",
        "ticket_id": ticket_id
    }), 201
# Get all tickets
@app.route("/api/tickets", methods=["GET"])
def get_tickets():

    conn = get_db_connection()

    tickets = conn.execute("""
        SELECT
            tickets.id,
            tickets.title,
            tickets.description,
            tickets.category,
            tickets.priority,
            tickets.status,
            tickets.assigned_to,
            tickets.resolution,
            tickets.created_at,
            tickets.due_at,
            users.name AS user_name
        FROM tickets
        JOIN users ON tickets.user_id = users.id
        ORDER BY tickets.created_at DESC
    """).fetchall()

    conn.close()

    return jsonify([dict(ticket) for ticket in tickets])


# Get one ticket
@app.route("/api/tickets/<int:ticket_id>", methods=["GET"])
def get_ticket(ticket_id):

    if "user_id" not in session:
        return jsonify({"error": "Login required"}), 401

    conn = get_db_connection()

    ticket = conn.execute("""
        SELECT
            tickets.*,
            users.name AS user_name
        FROM tickets
        JOIN users
            ON tickets.user_id = users.id
        WHERE tickets.id = ?
    """, (ticket_id,)).fetchone()

    if ticket is None:
        conn.close()
        return jsonify({"error": "Ticket not found"}), 404

    user_id = session["user_id"]
    role = session["role"]

    if role == "support" and ticket["assigned_to"] != user_id:
        conn.close()
        return jsonify({"error": "Access denied"}), 403

    if role == "user" and ticket["user_id"] != user_id:
        conn.close()
        return jsonify({"error": "Access denied"}), 403

    conn.close()

    return jsonify(dict(ticket))
# Update ticket status
@app.route("/api/tickets/<int:ticket_id>/status", methods=["PUT"])
def update_status(ticket_id):

    if "user_id" not in session:
        return jsonify({"error": "Login required"}), 401

    if session["role"] != "support":
        return jsonify({"error": "Only support staff can update status"}), 403

    data = request.get_json()

    status = data.get("status")

    allowed_statuses = [
        "Assigned",
        "In Progress",
        "Resolved"
    ]

    if status not in allowed_statuses:
        return jsonify({"error": "Invalid status"}), 400

    conn = get_db_connection()

    ticket = conn.execute("""
        SELECT id
        FROM tickets
        WHERE id = ? AND assigned_to = ?
    """, (
        ticket_id,
        session["user_id"]
    )).fetchone()

    if ticket is None:
        conn.close()

        return jsonify({
            "error": "Ticket not found or not assigned to you"
        }), 404

    conn.execute("""
        UPDATE tickets
        SET status = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (
        status,
        ticket_id
    ))

    conn.commit()
    conn.close()

    return jsonify({
        "message": "Ticket status updated successfully"
    })

# Assign ticket to support staff
@app.route("/api/tickets/<int:ticket_id>/assign", methods=["PUT"])
def assign_ticket(ticket_id):

    data = request.get_json()
    assigned_to = data.get("assigned_to")

    conn = get_db_connection()

    staff = conn.execute("""
        SELECT id
        FROM users
        WHERE id = ? AND role = 'support'
    """, (assigned_to,)).fetchone()

    if staff is None:
        conn.close()
        return jsonify({
            "error": "Support staff not found"
        }), 404

    cursor = conn.execute("""
        UPDATE tickets
        SET assigned_to = ?,
            status = 'Assigned',
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (assigned_to, ticket_id))

    conn.commit()

    if cursor.rowcount == 0:
        conn.close()
        return jsonify({"error": "Ticket not found"}), 404

    conn.close()

    return jsonify({
        "message": "Ticket assigned successfully"
    })


# Resolve ticket
@app.route("/api/tickets/<int:ticket_id>/resolve", methods=["PUT"])
def resolve_ticket(ticket_id):

    if "user_id" not in session:
        return jsonify({"error": "Login required"}), 401

    if session["role"] != "support":
        return jsonify({
            "error": "Only support staff can resolve tickets"
        }), 403

    data = request.get_json()

    resolution = data.get("resolution")

    if not resolution:
        return jsonify({
            "error": "Resolution details are required"
        }), 400

    conn = get_db_connection()

    ticket = conn.execute("""
        SELECT id
        FROM tickets
        WHERE id = ? AND assigned_to = ?
    """, (
        ticket_id,
        session["user_id"]
    )).fetchone()

    if ticket is None:
        conn.close()

        return jsonify({
            "error": "Ticket not found or not assigned to you"
        }), 404

    conn.execute("""
        UPDATE tickets
        SET resolution = ?,
            status = 'Resolved',
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (
        resolution,
        ticket_id
    ))

    conn.commit()
    conn.close()

    return jsonify({
        "message": "Ticket resolved successfully"
    })
@app.route("/api/login", methods=["POST"])
def login():

    data = request.get_json()
    if not data:
        return jsonify({"error": "Request data is required"}), 400

    email = data.get("email", "").strip()
    password = data.get("password", "")

    if not email or not password:
        return jsonify({
            "error": "Email and password are required"
        }), 400

    conn = get_db_connection()

    user = conn.execute("""
        SELECT id, name, email, password_hash, role
        FROM users
        WHERE email = ?
    """, (email,)).fetchone()

    conn.close()

    if user is None:
        return jsonify({
            "error": "Invalid email or password"
        }), 401

    if not check_password_hash(user["password_hash"], password):
        return jsonify({
            "error": "Invalid email or password"
        }), 401

    session["user_id"] = user["id"]
    session["role"] = user["role"]

    return jsonify({
        "message": "Login successful",
        "user": {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "role": user["role"]
        }
    })
@app.route("/api/logout", methods=["POST"])
def logout():

    session.clear()

    return jsonify({
        "message": "Logout successful"
    })
if __name__ == "__main__":
    app.run(debug=True)