import os, secrets, datetime
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

app = Flask(__name__, static_folder='.')
CORS(app)

# Config
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'ikokitufiti-secret-2026')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///ikokitufiti.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5MB max - for clear photos

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
db = SQLAlchemy(app)

# MODELS
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(80), nullable=False)
    last_name = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    reset_token = db.Column(db.String(100), nullable=True)
    reset_expires = db.Column(db.DateTime, nullable=True)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    price = db.Column(db.Integer, nullable=False)
    category = db.Column(db.String(50))
    description = db.Column(db.String(500))
    image_path = db.Column(db.String(300))
    user_email = db.Column(db.String(120))
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

with app.app_context():
    db.create_all()

# FRONTEND
@app.route('/')
def home():
    return send_from_directory('.', 'index.html')

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# AUTH APIs
@app.route('/api/signup', methods=['POST'])
def signup():
    data = request.json
    if not data.get('email') or not data.get('password'):
        return jsonify({"error": "Email and password required"}), 400
    if len(data['password']) < 8:
        return jsonify({"error": "Password min 8 chars"}), 400
    if User.query.filter_by(email=data['email']).first():
        return jsonify({"error": "Email already exists"}), 400
    
    user = User(
        first_name=data.get('firstName',''),
        last_name=data.get('lastName',''),
        email=data['email'].lower().strip(),
        phone=data.get('phone',''),
        password_hash=generate_password_hash(data['password'])
    )
    db.session.add(user)
    db.session.commit()
    return jsonify({"message": "Account created!", "user": user.email})

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    user = User.query.filter_by(email=data.get('email','').lower().strip()).first()
    if not user or not check_password_hash(user.password_hash, data.get('password','')):
        return jsonify({"error": "Invalid email or password"}), 401
    return jsonify({"message": "Login success", "name": user.first_name, "email": user.email})

@app.route('/api/forgot-password', methods=['POST'])
def forgot_password():
    data = request.json
    user = User.query.filter_by(email=data.get('email','').lower().strip()).first()
    if not user:
        # For security, don't tell if email exists
        return jsonify({"message": "If email exists, reset link sent"})
    
    token = secrets.token_urlsafe(32)
    user.reset_token = token
    user.reset_expires = datetime.datetime.utcnow() + datetime.timedelta(minutes=15)
    db.session.commit()
    
    # In production, send email here via Resend/SendGrid
    # For now, return token for frontend demo (REMOVE in production)
    reset_link = f"/reset?token={token}"
    print(f"RESET LINK FOR {user.email}: {reset_link}")
    
    return jsonify({
        "message": f"Reset link sent to {user.email}",
        "demo_token": token,  # REMOVE THIS when you add real email
        "reset_link": reset_link
    })

@app.route('/api/reset-password', methods=['POST'])
def reset_password():
    data = request.json
    user = User.query.filter_by(reset_token=data.get('token')).first()
    if not user or user.reset_expires < datetime.datetime.utcnow():
        return jsonify({"error": "Invalid or expired token"}), 400
    
    user.password_hash = generate_password_hash(data['newPassword'])
    user.reset_token = None
    user.reset_expires = None
    db.session.commit()
    return jsonify({"message": "Password reset successful! Please login."})

# PRODUCT APIs
@app.route('/api/products', methods=['GET'])
def get_products():
    products = Product.query.order_by(Product.created_at.desc()).all()
    return jsonify([{
        "id": p.id, "name": p.name, "price": p.price, 
        "category": p.category, "description": p.description,
        "image": f"/uploads/{os.path.basename(p.image_path)}" if p.image_path else "",
        "date": p.created_at.isoformat()
    } for p in products])

@app.route('/api/products', methods=['POST'])
def add_product():
    # Support both JSON with base64 and form-data
    if request.content_type and 'multipart/form-data' in request.content_type:
        name = request.form.get('name')
        price = request.form.get('price')
        category = request.form.get('category')
        description = request.form.get('description')
        user_email = request.form.get('user_email','guest')
        file = request.files.get('image')
        image_path = ""
        if file and file.filename:
            filename = secure_filename(f"{secrets.token_hex(8)}_{file.filename}")
            save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(save_path)
            image_path = save_path
    else:
        data = request.json
        name = data.get('name')
        price = data.get('price')
        category = data.get('category')
        description = data.get('description')
        user_email = data.get('user_email','guest')
        image_path = ""  # Frontend will send file separately

    if not name or not price:
        return jsonify({"error": "Name and price required"}), 400

    product = Product(
        name=name, price=int(price), category=category,
        description=description, image_path=image_path,
        user_email=user_email
    )
    db.session.add(product)
    db.session.commit()
    return jsonify({"message": "Product uploaded!", "id": product.id})

@app.route('/api/upload', methods=['POST'])
def upload_image():
    if 'image' not in request.files:
        return jsonify({"error": "No image"}), 400
    file = request.files['image']
    if file.filename == '':
        return jsonify({"error": "No file"}), 400
    if file:
        filename = secure_filename(f"{secrets.token_hex(10)}_{file.filename}")
        save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(save_path)
        return jsonify({"url": f"/uploads/{filename}", "path": save_path})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))
