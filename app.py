from flask import Flask, request, jsonify, render_template, session, redirect, url_for, flash, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_migrate import Migrate
from datetime import datetime
import os
import logging
from functools import wraps
import qrcode
import io
import base64
import uuid
import json
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # Required for session management
CORS(app)

# Database configuration
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'epass.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Error handlers
@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal Server Error: {str(error)}")
    return jsonify({'error': 'Internal Server Error', 'message': str(error)}), 500

@app.errorhandler(404)
def not_found_error(error):
    return jsonify({'error': 'Not Found', 'message': str(error)}), 404

# Admin decorator
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_id' not in session:
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

# Models
class Admin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)

class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    college_id = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(20), default='ACTIVE')

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'full_name': self.full_name,
            'phone': self.phone,
            'college_id': self.college_id,
            'status': self.status
        }

class Bus(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    bus_number = db.Column(db.String(20), nullable=False)
    source = db.Column(db.String(100), nullable=False)
    destination = db.Column(db.String(100), nullable=False)
    departure_time = db.Column(db.String(20), nullable=False)
    available_seats = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'bus_number': self.bus_number,
            'source': self.source,
            'destination': self.destination,
            'departure_time': self.departure_time,
            'available_seats': self.available_seats,
            'price': self.price
        }

class Epass(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    bus_id = db.Column(db.Integer, db.ForeignKey('bus.id'), nullable=False)
    booking_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    travel_date = db.Column(db.Date, nullable=False)
    payment_id = db.Column(db.String(100), nullable=True)
    status = db.Column(db.String(20), nullable=False, default='ACTIVE')
    seat_number = db.Column(db.String(10), nullable=True)

class SeatReservation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    bus_id = db.Column(db.Integer, db.ForeignKey('bus.id'), nullable=False)
    seat_number = db.Column(db.String(10), nullable=False)
    travel_date = db.Column(db.Date, nullable=False)
    reason = db.Column(db.String(200), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    # Unique constraint to prevent duplicate reservations
    __table_args__ = (
        db.UniqueConstraint('bus_id', 'seat_number', 'travel_date', name='unique_seat_reservation'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'bus_id': self.bus_id,
            'seat_number': self.seat_number,
            'travel_date': self.travel_date.strftime('%Y-%m-%d'),
            'reason': self.reason,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S')
        }

class Route(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    route_id = db.Column(db.String(50), unique=True, nullable=False)
    bus_id = db.Column(db.Integer, db.ForeignKey('bus.id'), nullable=False)
    stop_name = db.Column(db.String(100), nullable=False)
    reach_time = db.Column(db.Time, nullable=False)

class GPSTracking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tracking_id = db.Column(db.String(50), unique=True, nullable=False)
    bus_id = db.Column(db.Integer, db.ForeignKey('bus.id'), nullable=False)
    latitude = db.Column(db.Float(precision=6), nullable=False)
    longitude = db.Column(db.Float(precision=6), nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    notification_id = db.Column(db.String(50), unique=True, nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    message = db.Column(db.String(500), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    payment_id = db.Column(db.String(50), unique=True, nullable=False)
    booking_id = db.Column(db.Integer, db.ForeignKey('epass.id'), nullable=False)
    upi_id = db.Column(db.String(50), nullable=False)
    transaction_id = db.Column(db.String(100), unique=True, nullable=False)
    payment_time = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    status = db.Column(db.Enum('Success', 'Failed', 'Pending'), nullable=False, default='Pending')

# Routes
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('index'))
    user = Student.query.get(session['user_id'])
    return render_template('dashboard.html', user=user)

@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    
    if Student.query.filter_by(username=data['username']).first():
        return jsonify({'error': 'Username already exists'}), 400
        
    if Student.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'Email already exists'}), 400
    
    new_student = Student(
        username=data['username'],
        email=data['email'],
        password=data['password'],
        full_name=data['full_name'],
        phone=data['phone'],
        college_id=data['college_id']
    )
    
    db.session.add(new_student)
    db.session.commit()
    
    return jsonify({'message': 'Registration successful'}), 201

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    student = Student.query.filter_by(username=data['username']).first()
    
    if student and student.password == data['password']:
        session['user_id'] = student.id
        return jsonify(student.to_dict())
    return jsonify({'error': 'Invalid credentials'}), 401

@app.route('/api/logout')
def logout():
    session.pop('user_id', None)
    return jsonify({'message': 'Logged out successfully'})

@app.route('/api/search-buses', methods=['POST'])
def search_buses():
    data = request.get_json()
    source = data['source'].strip().title()  # Capitalize first letter of each word
    destination = data['destination'].strip().title()
    
    # Case-insensitive search
    buses = Bus.query.filter(
        Bus.source.ilike(f"%{source}%"),
        Bus.destination.ilike(f"%{destination}%")
    ).all()
    
    return jsonify([{
        'id': bus.id,
        'bus_number': bus.bus_number,
        'departure_time': bus.departure_time,
        'available_seats': bus.available_seats,
        'price': bus.price,
        'source': bus.source,
        'destination': bus.destination
    } for bus in buses])

@app.route('/api/book-epass', methods=['POST'])
def book_epass():
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    data = request.get_json()
    bus = Bus.query.get(data['bus_id'])
    
    if not bus or bus.available_seats < 1:
        return jsonify({'error': 'No seats available'}), 400
    
    new_epass = Epass(
        student_id=session['user_id'],
        bus_id=data['bus_id'],
        travel_date=datetime.strptime(data['travel_date'], '%Y-%m-%d').date(),
        payment_id=data['payment_id']
    )
    
    bus.available_seats -= 1
    db.session.add(new_epass)
    db.session.commit()
    
    return jsonify({'message': 'E-pass booked successfully', 'epass_id': new_epass.id})

@app.route('/api/my-passes')
def get_passes():
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    passes = Epass.query.filter_by(student_id=session['user_id']).all()
    return jsonify([{
        'id': epass.id,
        'travel_date': epass.travel_date.strftime('%Y-%m-%d'),
        'bus': Bus.query.get(epass.bus_id).bus_number,
        'status': epass.status
    } for epass in passes])

# Admin routes
@app.route('/admin')
def admin_login_page():
    if 'admin_id' in session:
        return redirect(url_for('admin_dashboard'))
    return render_template('admin/login.html')

@app.route('/admin/login', methods=['POST'])
def admin_login():
    data = request.get_json()
    admin = Admin.query.filter_by(username=data['username']).first()
    
    if admin and admin.password == data['password']:
        session['admin_id'] = admin.id
        return jsonify({'message': 'Login successful'})
    return jsonify({'error': 'Invalid credentials'}), 401

@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    return render_template('admin/dashboard.html')

@app.route('/admin/buses')
@admin_required
def admin_buses():
    buses = Bus.query.all()
    return render_template('admin/buses.html', buses=buses)

@app.route('/admin/students')
@admin_required
def admin_students():
    students = Student.query.all()
    return render_template('admin/students.html', students=students)

# Admin API routes
@app.route('/api/admin/bus', methods=['POST'])
@admin_required
def add_bus():
    data = request.get_json()
    new_bus = Bus(**data)
    db.session.add(new_bus)
    db.session.commit()
    return jsonify({'message': 'Bus added successfully', 'bus': new_bus.to_dict()})

@app.route('/api/admin/bus/<int:bus_id>', methods=['PUT'])
@admin_required
def update_bus(bus_id):
    data = request.get_json()
    bus = Bus.query.get_or_404(bus_id)
    for key, value in data.items():
        setattr(bus, key, value)
    db.session.commit()
    return jsonify({'message': 'Bus updated successfully', 'bus': bus.to_dict()})

@app.route('/api/admin/bus/<int:bus_id>', methods=['DELETE'])
@admin_required
def delete_bus(bus_id):
    bus = Bus.query.get_or_404(bus_id)
    db.session.delete(bus)
    db.session.commit()
    return jsonify({'message': 'Bus deleted successfully'})

@app.route('/api/admin/student/<int:student_id>', methods=['PUT'])
@admin_required
def update_student(student_id):
    data = request.get_json()
    student = Student.query.get_or_404(student_id)
    for key, value in data.items():
        setattr(student, key, value)
    db.session.commit()
    return jsonify({'message': 'Student updated successfully', 'student': student.to_dict()})

@app.route('/api/admin/student/<int:student_id>', methods=['DELETE'])
@admin_required
def delete_student(student_id):
    student = Student.query.get_or_404(student_id)
    db.session.delete(student)
    db.session.commit()
    return jsonify({'message': 'Student deleted successfully'})

# GPS Tracking Routes
@app.route('/api/gps/update', methods=['POST'])
@admin_required
def update_gps():
    data = request.get_json()
    tracking = GPSTracking(
        tracking_id=data['tracking_id'],
        bus_id=data['bus_id'],
        latitude=data['latitude'],
        longitude=data['longitude']
    )
    db.session.add(tracking)
    db.session.commit()
    return jsonify({'message': 'GPS location updated successfully'})

@app.route('/api/gps/bus/<int:bus_id>')
def get_bus_location(bus_id):
    tracking = GPSTracking.query.filter_by(bus_id=bus_id).order_by(GPSTracking.timestamp.desc()).first()
    if not tracking:
        return jsonify({'error': 'No GPS data available for this bus'}), 404
    return jsonify({
        'bus_id': tracking.bus_id,
        'latitude': tracking.latitude,
        'longitude': tracking.longitude,
        'last_updated': tracking.timestamp.isoformat()
    })

# Route Management Routes
@app.route('/api/admin/routes', methods=['POST'])
@admin_required
def add_route():
    data = request.get_json()
    route = Route(
        route_id=data['route_id'],
        bus_id=data['bus_id'],
        stop_name=data['stop_name'],
        reach_time=datetime.strptime(data['reach_time'], '%H:%M').time()
    )
    db.session.add(route)
    db.session.commit()
    return jsonify({'message': 'Route added successfully'})

@app.route('/api/routes/bus/<int:bus_id>')
def get_bus_routes(bus_id):
    routes = Route.query.filter_by(bus_id=bus_id).all()
    return jsonify([{
        'route_id': route.route_id,
        'stop_name': route.stop_name,
        'reach_time': route.reach_time.strftime('%H:%M')
    } for route in routes])

# Notification Routes
@app.route('/api/notifications/student/<int:student_id>')
def get_student_notifications(student_id):
    notifications = Notification.query.filter_by(student_id=student_id).order_by(Notification.created_at.desc()).all()
    return jsonify([{
        'notification_id': notif.notification_id,
        'message': notif.message,
        'created_at': notif.created_at.isoformat()
    } for notif in notifications])

@app.route('/api/admin/notifications', methods=['POST'])
@admin_required
def send_notification():
    data = request.get_json()
    notification = Notification(
        notification_id=data['notification_id'],
        student_id=data['student_id'],
        message=data['message']
    )
    db.session.add(notification)
    db.session.commit()
    return jsonify({'message': 'Notification sent successfully'})

# Payment Routes
@app.route('/api/payments/process', methods=['POST'])
def process_payment():
    data = request.get_json()
    payment = Payment(
        payment_id=data['payment_id'],
        booking_id=data['booking_id'],
        upi_id=data['upi_id'],
        transaction_id=data['transaction_id']
    )
    db.session.add(payment)
    db.session.commit()
    
    # Update the corresponding e-pass status
    epass = Epass.query.get(data['booking_id'])
    if epass:
        epass.payment_id = payment.payment_id
        db.session.commit()
    
    return jsonify({
        'message': 'Payment processed successfully',
        'payment_id': payment.payment_id,
        'status': payment.status
    })

@app.route('/api/payments/<payment_id>')
def get_payment_status(payment_id):
    payment = Payment.query.filter_by(payment_id=payment_id).first()
    if not payment:
        return jsonify({'error': 'Payment not found'}), 404
    return jsonify({
        'payment_id': payment.payment_id,
        'status': payment.status,
        'transaction_id': payment.transaction_id,
        'payment_time': payment.payment_time.isoformat()
    })

@app.route('/api/admin/payments/verify', methods=['POST'])
@admin_required
def verify_payment():
    data = request.get_json()
    payment = Payment.query.filter_by(payment_id=data['payment_id']).first()
    if not payment:
        return jsonify({'error': 'Payment not found'}), 404
    
    payment.status = data['status']
    db.session.commit()
    return jsonify({'message': 'Payment status updated successfully'})

@app.route('/book/<int:bus_id>')
def book_bus(bus_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    bus = Bus.query.get_or_404(bus_id)
    travel_date = request.args.get('date')
    
    if not travel_date:
        return redirect(url_for('dashboard'))
    
    return render_template('book.html', bus=bus, travel_date=travel_date)

@app.route('/payment/<int:booking_id>')
def payment(booking_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    booking = Epass.query.get_or_404(booking_id)
    if booking.student_id != session['user_id']:
        flash('Unauthorized access')
        return redirect(url_for('dashboard'))
        
    bus = Bus.query.get(booking.bus_id)
    student = Student.query.get(booking.student_id)
    
    booking_data = {
        'id': booking.id,
        'route': f"{bus.source} to {bus.destination}",
        'date': booking.travel_date.strftime('%Y-%m-%d'),
        'seat_number': booking.seat_number,
        'amount': bus.price
    }
    
    return render_template('payment.html', booking=booking_data)

@app.route('/process_payment', methods=['POST'])
def process_payment_and_generate_ticket():
    try:
        booking_id = request.form.get('booking_id')
        booking = Epass.query.get_or_404(booking_id)
        
        # Update booking status to confirmed (dummy payment always succeeds)
        booking.status = 'CONFIRMED'
        booking.payment_id = str(uuid.uuid4())  # Generate dummy payment ID
        db.session.commit()
        
        # Generate QR code
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr_data = {
            'ticket_id': booking.id,
            'student_id': booking.student_id,
            'bus_id': booking.bus_id,
            'travel_date': booking.travel_date.strftime('%Y-%m-%d'),
            'seat_number': booking.seat_number
        }
        qr.add_data(str(qr_data))
        qr.make(fit=True)
        
        # Create QR code image
        qr_img = qr.make_image(fill_color="black", back_color="white")
        buffered = io.BytesIO()
        qr_img.save(buffered, format="PNG")
        qr_code_base64 = base64.b64encode(buffered.getvalue()).decode()
        
        # Get related data
        student = Student.query.get(booking.student_id)
        bus = Bus.query.get(booking.bus_id)
        
        # Prepare ticket data
        ticket_data = {
            'id': booking.id,
            'student_name': student.full_name,
            'route': f"{bus.source} to {bus.destination}",
            'date': booking.travel_date.strftime('%Y-%m-%d'),
            'seat_number': booking.seat_number,
            'amount': bus.price,
            'qr_code': f"data:image/png;base64,{qr_code_base64}"
        }
        
        return render_template('ticket.html', ticket=ticket_data)
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/download_ticket/<int:ticket_id>')
def download_ticket(ticket_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    booking = Epass.query.get_or_404(ticket_id)
    if booking.student_id != session['user_id']:
        flash('Unauthorized access')
        return redirect(url_for('dashboard'))
    
    # Generate QR code
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr_data = {
        'ticket_id': booking.id,
        'student_id': booking.student_id,
        'bus_id': booking.bus_id,
        'travel_date': booking.travel_date.strftime('%Y-%m-%d'),
        'seat_number': booking.seat_number
    }
    qr.add_data(str(qr_data))
    qr.make(fit=True)
    
    # Create QR code image
    qr_img = qr.make_image(fill_color="black", back_color="white")
    buffered = io.BytesIO()
    qr_img.save(buffered, format="PNG")
    
    # Get related data
    student = Student.query.get(booking.student_id)
    bus = Bus.query.get(booking.bus_id)
    
    # Create a new image with ticket details
    from PIL import Image, ImageDraw, ImageFont
    import os
    
    # Create a new image with white background
    width = 800
    height = 400
    img = Image.new('RGB', (width, height), 'white')
    draw = ImageDraw.Draw(img)
    
    # Add ticket details
    try:
        # Try to use a system font
        font = ImageFont.truetype("arial.ttf", 20)
    except:
        # Fallback to default font
        font = ImageFont.load_default()
    
    # Draw ticket details
    draw.text((50, 50), f"Ticket ID: {booking.id}", font=font, fill='black')
    draw.text((50, 80), f"Student: {student.full_name}", font=font, fill='black')
    draw.text((50, 110), f"Route: {bus.source} to {bus.destination}", font=font, fill='black')
    draw.text((50, 140), f"Date: {booking.travel_date.strftime('%Y-%m-%d')}", font=font, fill='black')
    draw.text((50, 170), f"Seat: {booking.seat_number}", font=font, fill='black')
    
    # Paste QR code
    qr_img = qr_img.resize((150, 150))  # Resize QR code
    img.paste(qr_img, (width-200, 50))
    
    # Save the final image
    output = io.BytesIO()
    img.save(output, format='PNG')
    output.seek(0)
    
    return send_file(
        output,
        mimetype='image/png',
        as_attachment=True,
        download_name=f'ticket_{booking.id}.png'
    )

@app.route('/api/check-seats', methods=['POST'])
def check_seats():
    data = request.get_json()
    bus_id = data.get('bus_id')
    travel_date = data.get('travel_date')
    
    if not bus_id or not travel_date:
        return jsonify({'error': 'Bus ID and travel date are required'}), 400
    
    try:
        travel_date = datetime.strptime(travel_date, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'error': 'Invalid date format'}), 400
    
    bus = Bus.query.get_or_404(bus_id)
    
    # Get all booked seats for this date
    booked_seats = Epass.query.filter_by(
        bus_id=bus_id,
        travel_date=travel_date,
        status='ACTIVE'
    ).with_entities(Epass.seat_number).all()
    booked_seats = [str(s[0]) for s in booked_seats]
    
    # Get all reserved seats for this date
    reserved_seats = SeatReservation.query.filter_by(
        bus_id=bus_id,
        travel_date=travel_date
    ).with_entities(SeatReservation.seat_number).all()
    reserved_seats = [str(s[0]) for s in reserved_seats]
    
    # Combine booked and reserved seats
    unavailable_seats = booked_seats + reserved_seats
    
    # Check if there are any available seats
    total_seats = 45  # Fixed total seats for all buses
    available_seats = total_seats - len(unavailable_seats)
    
    return jsonify({
        'available': available_seats > 0,
        'unavailable_seats': unavailable_seats,
        'total_seats': total_seats,
        'available_seats': available_seats,
        'booked_seats': booked_seats,
        'reserved_seats': reserved_seats
    })

@app.route('/book/<int:bus_id>/ticket', methods=['POST'])
def book_ticket(bus_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    travel_date = request.form.get('travel_date')
    seat_number = request.form.get('seat_number')
    
    if not travel_date or not seat_number:
        flash('Please select a travel date and seat number')
        return redirect(url_for('book_bus', bus_id=bus_id))
    
    try:
        travel_date = datetime.strptime(travel_date, '%Y-%m-%d').date()
    except ValueError:
        flash('Invalid date format')
        return redirect(url_for('book_bus', bus_id=bus_id))
    
    bus = Bus.query.get_or_404(bus_id)
    
    # Check if seat is already booked for this date
    existing_booking = Epass.query.filter_by(
        bus_id=bus_id,
        travel_date=travel_date,
        seat_number=seat_number,
        status='ACTIVE'
    ).first()
    
    if existing_booking:
        flash('This seat is already booked for the selected date')
        return redirect(url_for('book_bus', bus_id=bus_id))
    
    # Check if seat is reserved for this date
    existing_reservation = SeatReservation.query.filter_by(
        bus_id=bus_id,
        travel_date=travel_date,
        seat_number=seat_number
    ).first()
    
    if existing_reservation:
        flash('This seat is reserved and not available for booking')
        return redirect(url_for('book_bus', bus_id=bus_id))
    
    # Create booking with pending status
    booking = Epass(
        student_id=session['user_id'],
        bus_id=bus_id,
        travel_date=travel_date,
        seat_number=seat_number,
        status='PENDING',
        payment_id=None
    )
    
    try:
        db.session.add(booking)
        db.session.commit()
        
        # Redirect to payment page
        return redirect(url_for('payment', booking_id=booking.id))
        
    except Exception as e:
        db.session.rollback()
        flash('Error creating booking. Please try again.')
        return redirect(url_for('book_bus', bus_id=bus_id))

@app.route('/api/admin/bus/<int:bus_id>/seats')
@admin_required
def get_bus_seats(bus_id):
    date = request.args.get('date')
    if not date:
        return jsonify({'error': 'Date parameter is required'}), 400
    
    try:
        date = datetime.strptime(date, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'error': 'Invalid date format'}), 400
    
    # Get all booked seats for this date
    booked_seats = Epass.query.filter_by(
        bus_id=bus_id,
        travel_date=date,
        status='ACTIVE'
    ).with_entities(Epass.seat_number).all()
    booked_seats = [str(s[0]) for s in booked_seats]
    
    # Get all reserved seats for this date
    reserved_seats = SeatReservation.query.filter_by(
        bus_id=bus_id,
        travel_date=date
    ).with_entities(SeatReservation.seat_number).all()
    reserved_seats = [str(s[0]) for s in reserved_seats]
    
    return jsonify({
        'booked_seats': booked_seats,
        'reserved_seats': reserved_seats,
        'total_seats': 45,  # Fixed total seats for all buses
        'available_seats': 45 - (len(booked_seats) + len(reserved_seats))
    })

@app.route('/api/admin/bus/<int:bus_id>/seats', methods=['POST'])
@admin_required
def reserve_seat(bus_id):
    data = request.get_json()
    seat_number = data.get('seat_number')
    travel_date = data.get('travel_date')
    reason = data.get('reason', '')
    
    if not seat_number or not travel_date:
        return jsonify({'error': 'Seat number and travel date are required'}), 400
    
    try:
        travel_date = datetime.strptime(travel_date, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'error': 'Invalid date format'}), 400
    
    # Check if seat is already booked
    existing_booking = Epass.query.filter_by(
        bus_id=bus_id,
        travel_date=travel_date,
        seat_number=seat_number,
        status='ACTIVE'
    ).first()
    
    if existing_booking:
        return jsonify({'error': 'This seat is already booked'}), 400
    
    # Check if seat is already reserved
    existing_reservation = SeatReservation.query.filter_by(
        bus_id=bus_id,
        travel_date=travel_date,
        seat_number=seat_number
    ).first()
    
    if existing_reservation:
        return jsonify({'error': 'This seat is already reserved'}), 400
    
    # Create new reservation
    reservation = SeatReservation(
        bus_id=bus_id,
        seat_number=seat_number,
        travel_date=travel_date,
        reason=reason
    )
    
    try:
        db.session.add(reservation)
        db.session.commit()
        return jsonify({
            'message': 'Seat reserved successfully',
            'reservation': {
                'id': reservation.id,
                'seat_number': reservation.seat_number,
                'travel_date': reservation.travel_date.strftime('%Y-%m-%d'),
                'reason': reservation.reason
            }
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Error reserving seat'}), 500

@app.route('/api/admin/bus/<int:bus_id>/seats/<int:reservation_id>', methods=['DELETE'])
@admin_required
def delete_seat_reservation(bus_id, reservation_id):
    reservation = SeatReservation.query.get_or_404(reservation_id)
    
    if reservation.bus_id != bus_id:
        return jsonify({'error': 'Invalid reservation'}), 400
    
    try:
        db.session.delete(reservation)
        db.session.commit()
        return jsonify({'message': 'Reservation deleted successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Error deleting reservation'}), 500

# Initialize database after all models are defined
try:
    with app.app_context():
        db.create_all()  # Create tables
        # Create default admin if not exists
        if not Admin.query.filter_by(username='admin').first():
            admin = Admin(username='admin', password='admin123')
            db.session.add(admin)
            db.session.commit()
        logger.info("Database initialized successfully")
except Exception as e:
    logger.error(f"Error initializing database: {str(e)}")
    raise

if __name__ == '__main__':
    app.run(debug=True) 