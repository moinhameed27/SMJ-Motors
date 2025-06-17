from flask import Flask, render_template, request, redirect, url_for, session, flash
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

@app.route('/admin/dashboard')
def admin_dashboard():
    if 'email' in session and session['user_type'] == 'admin':
        services = list(mongo.db.services.find())
        wheels = list(mongo.db.wheels.find())
        appointments = list(mongo.db.appointments.find())
        return render_template('admin.html',
                            services=services,
                            wheels=wheels,
                            appointments=appointments)
    return redirect(url_for('login'))

@app.route('/user/dashboard')
def user_dashboard():
    if 'email' in session and session['user_type'] == 'user':
        return render_template('user.html')
    return redirect(url_for('login'))

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
    return render_template('services.html')

@app.route('/showroom')
def showroom():
    return render_template('showroom.html')

@app.route('/appointments')
def appointments():
    return render_template('appointments.html')

# Admin-specific pages
@app.route('/admin/services')
def admin_services():
    if 'email' in session and session['user_type'] == 'admin':
        return render_template('servicesA.html')
    return redirect(url_for('login'))

@app.route('/admin/showroom')
def admin_showroom():
    if 'email' in session and session['user_type'] == 'admin':
        return render_template('showroomA.html')
    return redirect(url_for('login'))

@app.route('/admin/appointments')
def admin_appointments():
    if 'email' in session and session['user_type'] == 'admin':
        return render_template('appointmentsA.html')
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
        return render_template('addappointment.html')
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
    flash('Appointment added successfully!')
    return redirect(url_for('admin_dashboard'))

# Add Service
@app.route('/add_service', methods=['POST'])
def add_service():
    service_data = {
        'name': request.form['name'],
        'type': request.form['type'],
        'description': request.form['description'],
        'price': float(request.form['price'])
    }
    mongo.db.services.insert_one(service_data)
    flash('Service added successfully!')
    return redirect(url_for('admin_dashboard'))


if __name__ == '__main__':
    app.run(debug=True)
