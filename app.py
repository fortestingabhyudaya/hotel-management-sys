from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
import json
import random
import os
import smtplib
from email.mime.text import MIMEText
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = "SuperSecretKeyForSession123!"

BOOKINGS_FILE = 'bookings.json'
HISTORY_FILE = 'history.json'

# ---------------- Staff & Owner Passwords ----------------
STAFF_PASSWORD = "EAAadmin123"
OWNER_PASSWORD = "EAAowner123"

# ---------------- Email Configuration ----------------
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")

def send_confirmation_email(to_email, name, room_number, check_in, check_out, room_type, price):
    """Send a booking confirmation email to the guest."""
    if not EMAIL_USER or not EMAIL_PASS:
        print("⚠️ Email credentials not found in environment variables.")
        return False

    subject = f"Booking Confirmation - Room {room_number}"
    body = f"""
Dear {name},

🎉 Your booking has been successfully confirmed!

📋 Booking Details:
Room Number: {room_number}
Room Type: {room_type}
Check-in Date: {check_in}
Check-out Date: {check_out}
Total Price: ₹{price}

Please check in before {check_in}.

Thank you for choosing Abhyudaya Residency Hotel!
Warm regards,
Abhyudaya Residency Management
"""

    try:
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = EMAIL_USER
        msg["To"] = to_email

        # Gmail SMTP
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASS)
            server.send_message(msg)

        print(f"✅ Confirmation email sent to {to_email}")
        return True

    except Exception as e:
        print(f"❌ Failed to send email: {e}")
        return False


# ---------------- Helper Functions ----------------
def load_bookings():
    if not os.path.exists(BOOKINGS_FILE):
        with open(BOOKINGS_FILE, 'w') as f:
            f.write('{"bookings": []}')
    try:
        with open(BOOKINGS_FILE, 'r') as f:
            return json.load(f)
    except json.JSONDecodeError:
        with open(BOOKINGS_FILE, 'w') as f:
            f.write('{"bookings": []}')
        return {"bookings": []}

def save_bookings(data):
    with open(BOOKINGS_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def load_history():
    if not os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'w') as f:
            f.write('{"bookings": []}')
    try:
        with open(HISTORY_FILE, 'r') as f:
            return json.load(f)
    except json.JSONDecodeError:
        with open(HISTORY_FILE, 'w') as f:
            f.write('{"bookings": []}')
        return {"bookings": []}

def save_history(data):
    with open(HISTORY_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def assign_room(room_type=None):
    floor = random.choice([1, 2, 3])
    room = random.randint(1, 8)
    return f"{floor}0{room}"

def calculate_price(room_type, check_in, check_out):
    price_map = {
        "AC Deluxe": 5000,
        "AC Standard": 3500,
        "Non-AC": 2500
    }
    price_per_day = price_map.get(room_type, 3000)
    fmt = "%Y-%m-%d"
    d1 = datetime.strptime(check_in, fmt)
    d2 = datetime.strptime(check_out, fmt)
    days = (d2 - d1).days
    if days == 0:
        days = 1
    return price_per_day * days

# ---------------- Routes ----------------
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/guest', methods=['GET', 'POST'])
def guest():
    return render_template('guest.html')

@app.route('/guest/confirmation')
def guest_confirmation():
    guest_info = {
        "name": request.args.get("name"),
        "room_number": request.args.get("room_number"),
        "check_in": request.args.get("check_in"),
        "check_out": request.args.get("check_out"),
        "room_type": request.args.get("room_type"),
        "price": request.args.get("price")
    }
    return render_template("guest_confirmation.html", guest=guest_info)

# ---------------- Staff Login ----------------
@app.route('/staff', methods=['GET', 'POST'])
def staff():
    if request.method == 'POST':
        password = request.form.get('password')
        if password == STAFF_PASSWORD:
            session['staff_logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        else:
            flash("Incorrect password! Try again.", "error")
            return redirect(url_for('staff'))

    if session.get('staff_logged_in'):
        return redirect(url_for('admin_dashboard'))

    return render_template('staff_login.html')

@app.route('/admin')
def admin_dashboard():
    if not session.get('staff_logged_in'):
        return redirect(url_for('staff'))
    return render_template('admin.html', bookings=load_bookings())

# ---------------- Owner Login ----------------
@app.route('/owner', methods=['GET', 'POST'])
def owner_login():
    if request.method == 'POST':
        password = request.form.get('password')
        if password == OWNER_PASSWORD:
            session['owner_logged_in'] = True
            return redirect(url_for('owner_dashboard'))
        else:
            flash("Incorrect password! Try again.", "error")
            return redirect(url_for('owner_login'))

    if session.get('owner_logged_in'):
        return redirect(url_for('owner_dashboard'))

    return render_template('owner_login.html')

@app.route('/owner/dashboard')
def owner_dashboard():
    if not session.get('owner_logged_in'):
        return redirect(url_for('owner_login'))

    current = load_bookings()
    history = load_history()
    return render_template('owner.html', bookings=current, past_bookings=history)

# ---------------- API Routes ----------------
@app.route('/api/bookings', methods=['GET'])
def get_bookings():
    return jsonify(load_bookings())

@app.route('/api/book', methods=['POST'])
def book_room():
    try:
        data = request.json
        if not data:
            return jsonify({"status": "error", "message": "No data received"}), 400

        data['room_number'] = assign_room(data.get('room_type'))
        data['price'] = calculate_price(data.get('room_type'), data.get('check_in'), data.get('check_out'))

        bookings = load_bookings()
        bookings['bookings'].append(data)
        save_bookings(bookings)

        # ✅ Send confirmation email
        send_confirmation_email(
            to_email=data.get("email"),
            name=data.get("name"),
            room_number=data['room_number'],
            check_in=data.get("check_in"),
            check_out=data.get("check_out"),
            room_type=data.get("room_type"),
            price=data['price']
        )

        return jsonify({"status": "success", "room": data['room_number']})
    except Exception as e:
        print("Booking error:", e)
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/checkout', methods=['POST'])
def checkout_room():
    try:
        data = request.json
        room_number = data.get('room_number')
        if not room_number:
            return jsonify({"status": "error", "message": "No room number provided"}), 400

        bookings = load_bookings()
        new_bookings = []
        completed_booking = None
        for b in bookings['bookings']:
            if b['room_number'] == room_number:
                completed_booking = b
            else:
                new_bookings.append(b)

        bookings['bookings'] = new_bookings
        save_bookings(bookings)

        if completed_booking:
            history = load_history()
            history['bookings'].append(completed_booking)
            save_history(history)

        return jsonify({"status": "success"})
    except Exception as e:
        print("Checkout error:", e)
        return jsonify({"status": "error", "message": str(e)}), 500

# ---------------- Run App ----------------
if __name__ == '__main__':
    app.run(debug=True)