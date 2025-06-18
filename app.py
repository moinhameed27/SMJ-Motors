from flask import jsonify, Flask, render_template, request, redirect, url_for, session, flash
from bson import ObjectId
import os
from flask_pymongo import PyMongo
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

app = Flask(__name__, template_folder='templates', static_folder='static')
app.secret_key = 'your-secret-key-here'

# MongoDB configuration
app.config["MONGO_URI"] = "mongodb://localhost:27017/smj_motors"
mongo = PyMongo(app)

# Admin credentials (email and password)
ADMIN_EMAIL = 'admin@smj.com'
ADMIN_PASSWORD = 'a'
# ADMIN_PASSWORD = 'admin123'

@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user_type = request.form.get('user_type')

        if user_type == 'admin':
            # Check admin credentials
            if email == ADMIN_EMAIL and password == ADMIN_PASSWORD:
                session['email'] = email
                session['user_type'] = 'admin'
                return redirect(url_for('admin_dashboard'))
            else:
                flash('Invalid admin credentials', 'error')
        else:
            # Check user credentials
            user = mongo.db.users.find_one({'email': email})
            if user and check_password_hash(user['password'], password):
                session['email'] = email
                session['user_type'] = 'user'
                return redirect(url_for('user_dashboard'))
            else:
                flash('Invalid email or password', 'error')
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return redirect(url_for('signup'))

        # Check if user already exists
        if mongo.db.users.find_one({'email': email}):
            flash('Email already registered', 'error')
            return redirect(url_for('signup'))

        # Hash password and save user
        hashed_password = generate_password_hash(password)
        mongo.db.users.insert_one({
            'name': name,
            'email': email,
            'phone': phone,
            'password': hashed_password
        })
        flash('Account created successfully! Please login.', 'success')
        return redirect(url_for('login'))
    return render_template('signup.html')

icon_map = {
    '1': '🏍️', '2': '🔧', '3': '🛞', '4': '🔋', '5': '🔍',
    '6': '🛠️', '7': '⚙️', '8': '🚗', '9': '🧰', '10': '❄️', '11': '🏠'
}

@app.route('/admin/dashboard')
def admin_dashboard():
    if 'email' in session and session['user_type'] == 'admin':
        services = list(mongo.db.services.find().sort('_id', -1).limit(3))
        wheels = list(mongo.db.wheels.find().sort('_id', -1).limit(3))
        appointments = list(mongo.db.appointments.find().sort('_id', -1).limit(3))
        vehicles = {str(v['_id']): v for v in mongo.db.wheels.find()}
        service_docs = {str(s['_id']): s for s in mongo.db.services.find()}
        for appt in appointments:
            appt['vehicle_name'] = vehicles.get(str(appt['vehicleN']), {}).get('model', 'Unknown')
            appt['service_name'] = service_docs.get(str(appt['service']), {}).get('name', 'Unknown')
        return render_template('admin.html',
                            services=services,
                            wheels=wheels,
                            appointments=appointments)
    return redirect(url_for('login'))

@app.route('/user/dashboard')
def user_dashboard():
    if 'email' not in session or session.get('user_type') != 'user':
        return redirect(url_for('login'))

    # Fetch user's vehicles (latest 3 or all, most recent first)
    user = mongo.db.users.find_one({'email': session['email']})
    user_vehicle_ids = user.get('vehicles', []) if user else []
    latest_vehicle_ids = user_vehicle_ids[-3:][::-1] if len(user_vehicle_ids) > 3 else user_vehicle_ids[::-1]
    user_vehicles = list(mongo.db.wheels.find({'_id': {'$in': [ObjectId(v) for v in latest_vehicle_ids]}})) if latest_vehicle_ids else []

    # Fetch user's appointments (soonest first)
    user_appointments = list(mongo.db.appointments.find({'customerE': session['email']}).sort('date', 1).limit(2))

    # Join service and vehicle names for appointments
    if user_appointments:
        all_services = list(mongo.db.services.find())
        all_user_vehicles = list(mongo.db.wheels.find({'_id': {'$in': [ObjectId(v) for v in user_vehicle_ids]}})) if user_vehicle_ids else []
        services_dict = {str(s['_id']): s['name'] for s in all_services}
        vehicles_dict = {str(v['_id']): v['model'] for v in all_user_vehicles}
        for appt in user_appointments:
            appt['service_name'] = services_dict.get(appt['service'], appt['service'])
            appt['vehicleN_name'] = vehicles_dict.get(appt['vehicleN'], appt['vehicleN'])

    # Latest 4 services for "Our Services" section
    services = list(mongo.db.services.find().sort('_id', -1).limit(4))

    return render_template(
        'user.html',
        services=services,
        icon_map=icon_map,
        user_vehicles=user_vehicles,
        user_appointments=user_appointments
    )

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# Example routes for other pages (add as needed)
@app.route('/about')
def about():
    return render_template('aboutus.html')

@app.route('/services')
def services():
    if 'email' in session and session['user_type'] == 'user':
        motorbike_services = list(mongo.db.services.find({'type': 'motorbike'}))
        car_services = list(mongo.db.services.find({'type': 'car'}))
        return render_template('services.html',
                        motorbike_services=motorbike_services,
                        car_services=car_services,
                        icon_map=icon_map)
    return redirect(url_for('login'))

@app.route('/showroom')
def showroom():
    if 'email' in session and session['user_type'] == 'user':
        motorbikes = list(mongo.db.wheels.find({'type': 'motorbike', 'status': 'available'}))
        cars = list(mongo.db.wheels.find({'type': 'car', 'status': 'available'}))
        return render_template('showroom.html', motorbikes=motorbikes, cars=cars)
    return redirect(url_for('login'))

@app.route('/myvehicles')
def my_vehicles():
    if 'email' not in session or session.get('user_type') != 'user':
        return redirect(url_for('login'))
    user = mongo.db.users.find_one({'email': session['email']})
    user_vehicle_ids = user.get('vehicles', []) if user else []
    user_vehicles = list(mongo.db.wheels.find({'_id': {'$in': [ObjectId(v) for v in user_vehicle_ids]}})) if user_vehicle_ids else []
    return render_template('myvehicles.html', user_vehicles=user_vehicles)

@app.route('/sell_vehicle', methods=['POST'])
def sell_vehicle():
    if 'email' not in session or session.get('user_type') != 'user':
        return jsonify({'success': False, 'error': 'Not logged in'}), 401
    vehicle_id = request.json['vehicle_id']
    # Mark vehicle as available
    mongo.db.wheels.update_one({'_id': ObjectId(vehicle_id)}, {'$set': {'status': 'available'}})
    # Remove vehicle from user's list
    mongo.db.users.update_one({'email': session['email']}, {'$pull': {'vehicles': vehicle_id}})
    return jsonify({'success': True})

@app.route('/purchase_vehicle', methods=['POST'])
def purchase_vehicle():
    if 'email' not in session or session.get('user_type') != 'user':
        return jsonify({'success': False, 'error': 'Not logged in'}), 401

    vehicle_id = request.json['vehicle_id']
    # Mark vehicle as sold
    mongo.db.wheels.update_one({'_id': ObjectId(vehicle_id)}, {'$set': {'status': 'sold'}})
    # Add vehicle to user's vehicles list using email
    mongo.db.users.update_one({'email': session['email']}, {'$push': {'vehicles': vehicle_id}})
    return jsonify({'success': True})


@app.route('/appointments')
def appointments():
    if 'email' not in session or session.get('user_type') != 'user':
        return redirect(url_for('login'))

    user = mongo.db.users.find_one({'email': session['email']})
    user_vehicle_ids = user.get('vehicles', []) if user else []
    all_user_vehicles = list(mongo.db.wheels.find({'_id': {'$in': [ObjectId(v) for v in user_vehicle_ids]}})) if user_vehicle_ids else []
    all_services = list(mongo.db.services.find())
    user_appointments = list(mongo.db.appointments.find({'customerE': session['email']}).sort('date', 1))

    # Join service and vehicle names for appointments
    services_dict = {str(s['_id']): s['name'] for s in all_services}
    vehicles_dict = {str(v['_id']): v['model'] for v in all_user_vehicles}
    for appt in user_appointments:
        appt['service_name'] = services_dict.get(appt['service'], appt['service'])
        appt['vehicleN_name'] = vehicles_dict.get(appt['vehicleN'], appt['vehicleN'])

    return render_template(
        'appointments.html',
        all_user_vehicles=all_user_vehicles,
        all_services=all_services,
        user_appointments=user_appointments
    )

@app.route('/cancel_appointment/<appointment_id>', methods=['POST'])
def cancel_appointment(appointment_id):
    if 'email' not in session or session.get('user_type') != 'user':
        return redirect(url_for('login'))
    result = mongo.db.appointments.delete_one({'_id': ObjectId(appointment_id), 'customerE': session['email']})
    if result.deleted_count:
        return redirect(url_for('user_dashboard'))
    else:
        # Optionally, flash a message or handle the error as needed
        return redirect(url_for('user_dashboard'))

@app.route('/book_appointment', methods=['POST'])
def book_appointment():
    if 'email' not in session or session.get('user_type') != 'user':
        return redirect(url_for('login'))
    # Get user info
    user = mongo.db.users.find_one({'email': session['email']})
    # Prepare appointment data
    appointment_data = {
        'customerN': user.get('name', ''),
        'customerE': session['email'],
        'vehicleT': request.form['vehicleT'],
        'vehicleN': request.form['vehicleN'],
        'service': request.form['service'],
        'date': request.form['date'],
        'time': request.form['time'],
        'status': 'pending',
        'notes': request.form.get('notes', '')
    }
    # Insert into appointments collection
    mongo.db.appointments.insert_one(appointment_data)
    return redirect(url_for('user_dashboard'))


# Admin-specific pages
@app.route('/admin/services')
def admin_services():
    if 'email' in session and session['user_type'] == 'admin':
        motorbike_services = list(mongo.db.services.find({'type': 'motorbike'}))
        car_services = list(mongo.db.services.find({'type': 'car'}))
        return render_template('servicesA.html',
                          motorbike_services=motorbike_services,
                          car_services=car_services,
                          icon_map=icon_map)
    return redirect(url_for('login'))

@app.route('/admin/showroom')
def admin_showroom():
    if 'email' in session and session['user_type'] == 'admin':
        motorbikes = list(mongo.db.wheels.find({'type': 'motorbike'}))
        cars = list(mongo.db.wheels.find({'type': 'car'}))
        return render_template('showroomA.html',
                          motorbikes=motorbikes,
                          cars=cars)
    return redirect(url_for('login'))

@app.route('/admin/appointments')
def admin_appointments():
    if 'email' in session and session['user_type'] == 'admin':
        appointments = list(mongo.db.appointments.find())
        vehicles = {str(v['_id']): v for v in mongo.db.wheels.find()}
        services = {str(s['_id']): s for s in mongo.db.services.find()}
        # Attach names to each appointment
        for appt in appointments:
            appt['vehicle_name'] = vehicles.get(str(appt['vehicleN']), {}).get('model', 'Unknown')
            appt['service_name'] = services.get(str(appt['service']), {}).get('name', 'Unknown')
        return render_template('appointmentsA.html', appointments=appointments)
    return redirect(url_for('login'))

@app.route('/admin/addservice')
def admin_addservice():
    if 'email' in session and session['user_type'] == 'admin':
        return render_template('addservice.html')
    return redirect(url_for('login'))

@app.route('/admin/addcar')
def admin_addcar():
    if 'email' in session and session['user_type'] == 'admin':
        return render_template('addcar.html')
    return redirect(url_for('login'))

@app.route('/admin/addappointment')
def admin_addappointment():
    if 'email' in session and session['user_type'] == 'admin':
        vehicles = list(mongo.db.wheels.find())
        services = list(mongo.db.services.find())
        return render_template('addappointment.html', vehicles=vehicles, services=services)
    return redirect(url_for('login'))

@app.route('/admin/about')
def about_admin():
    if 'email' in session and session['user_type'] == 'admin':
        return render_template('aboutusA.html')
    return redirect(url_for('login'))

# Configure upload folder (create this folder in your project)
UPLOAD_FOLDER = 'static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.route('/add_car', methods=['POST'])
def add_car():
    # Get form data
    type = request.form['type']
    model = request.form['model']
    year = int(request.form['year'])
    price = float(request.form['price'])
    description = request.form['description']
    status = request.form['status']

    # Handle file upload
    if 'image' not in request.files:
        return "No image uploaded", 400
    image = request.files['image']
    if image.filename == '':
        return "No image selected", 400
    if image:
        filename = secure_filename(image.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        image.save(filepath)
        image_url = url_for('static', filename=f'uploads/{filename}')
    else:
        return "Invalid image", 400

    # Store in MongoDB
    car_data = {
        'type': type,
        'model': model,
        'year': year,
        'price': price,
        'description': description,
        'status': status,
        'image_url': image_url
    }
    mongo.db.wheels.insert_one(car_data)

    return redirect(url_for('admin_dashboard'))

# Add Appointment Form (GET)
@app.route('/add_appointment')
def add_appointment_form():
    vehicles = list(mongo.db.wheels.find())
    services = list(mongo.db.services.find())
    return render_template('addappointment.html',
                          vehicles=vehicles,
                          services=services)

# Add Appointment
@app.route('/add_appointment', methods=['POST'])
def add_appointment():
    appointment_data = {
        'customerN': request.form['customerN'],
        'customerE': request.form['customerE'],
        'vehicleT': request.form['vehicleT'],
        'vehicleN': request.form['vehicleN'],
        'service': request.form['service'],
        'date': request.form['date'],
        'time': request.form['time'],
        'status': request.form['status'],
        'notes': request.form['notes']
    }
    mongo.db.appointments.insert_one(appointment_data)
    # flash('Appointment added successfully!')
    return redirect(url_for('admin_dashboard'))

# Add Service
@app.route('/add_service', methods=['POST'])
def add_service():
    service_data = {
        'icon': request.form['icon'],
        'name': request.form['name'],
        'type': request.form['type'],
        'description': request.form['description'],
        'price': float(request.form['price'])
    }
    mongo.db.services.insert_one(service_data)
    # flash('Service added successfully!')
    return redirect(url_for('admin_dashboard'))

# Edit Service
@app.route('/edit_service/<service_id>', methods=['GET', 'POST'])
def edit_service(service_id):
    if request.method == 'POST':
        # Update logic
        mongo.db.services.update_one(
            {'_id': ObjectId(service_id)},
            {'$set': {
                'icon': request.form['icon'],
                'name': request.form['name'],
                'type': request.form['type'],
                'description': request.form['description'],
                'price': float(request.form['price'])
            }}
        )
        return redirect(url_for('admin_dashboard'))
    service = mongo.db.services.find_one({'_id': ObjectId(service_id)})
    return render_template('editservice.html', service=service)

# Edit Car/Wheels
@app.route('/edit_car/<car_id>', methods=['GET', 'POST'])
def edit_car(car_id):
    car = mongo.db.wheels.find_one({'_id': ObjectId(car_id)})
    if request.method == 'POST':
        update_fields = {
            'type': request.form['type'],
            'model': request.form['model'],
            'year': int(request.form['year']),
            'price': float(request.form['price']),
            'description': request.form['description'],
            'status': request.form['status']
        }
        # Handle image upload if a new image is provided
        if 'image' in request.files and request.files['image'].filename:
            image = request.files['image']
            filename = secure_filename(image.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            image.save(filepath)
            update_fields['image_url'] = url_for('static', filename=f'uploads/{filename}')
        else:
            update_fields['image_url'] = request.form.get('existing_image', car.get('image_url'))
        mongo.db.wheels.update_one({'_id': ObjectId(car_id)}, {'$set': update_fields})
        return redirect(url_for('admin_dashboard'))
    return render_template('editcar.html', car=car)

# Edit Appointment Form (GET)
@app.route('/edit_appointment/<appointment_id>')
def edit_appointment_form(appointment_id):
    appointment = mongo.db.appointments.find_one({'_id': ObjectId(appointment_id)})
    vehicles = list(mongo.db.wheels.find())
    services = list(mongo.db.services.find())
    return render_template('editappointment.html',
                          appointment=appointment,
                          vehicles=vehicles,
                          services=services)

@app.route('/admin/editappointment/<appointment_id>')
def admin_editappointment(appointment_id):
    appointment = mongo.db.appointments.find_one({'_id': ObjectId(appointment_id)})
    vehicles = list(mongo.db.wheels.find())
    services = list(mongo.db.services.find())
    return render_template('editappointment.html', appointment=appointment, vehicles=vehicles, services=services)

# Edit Appointment
@app.route('/edit_appointment/<appointment_id>', methods=['GET', 'POST'])
def edit_appointment(appointment_id):
    if request.method == 'POST':
        mongo.db.appointments.update_one(
            {'_id': ObjectId(appointment_id)},
            {'$set': {
                'customerN': request.form['customerN'],
                'customerE': request.form['customerE'],
                'vehicleT': request.form['vehicleT'],
                'vehicleN': request.form['vehicleN'],
                'service': request.form['service'],
                'date': request.form['date'],
                'time': request.form['time'],
                'status': request.form['status'],
                'notes': request.form['notes']
            }}
        )
        return redirect(url_for('admin_dashboard'))
    appointment = mongo.db.appointments.find_one({'_id': ObjectId(appointment_id)})
    return render_template('editappointment.html', appointment=appointment)

# Delete routes for appointments
@app.route('/delete_appointment/<appointment_id>', methods=['POST'])
def delete_appointment(appointment_id):
    mongo.db.appointments.delete_one({'_id': ObjectId(appointment_id)})
    return redirect(url_for('admin_dashboard'))

# Delete routes for wheels
@app.route('/delete_wheel/<wheel_id>', methods=['POST'])
def delete_wheel(wheel_id):
    mongo.db.wheels.delete_one({'_id': ObjectId(wheel_id)})
    return redirect(url_for('admin_dashboard'))

# Delete routes for services
@app.route('/delete_service/<service_id>', methods=['POST'])
def delete_service(service_id):
    mongo.db.services.delete_one({'_id': ObjectId(service_id)})
    return redirect(url_for('admin_dashboard'))


if __name__ == '__main__':
    app.run(debug=True)
