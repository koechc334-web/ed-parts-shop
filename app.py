from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import sqlite3
from werkzeug.utils import secure_filename

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
DATABASE = 'edparts.db'

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute('''CREATE TABLE IF NOT EXISTS products 
                 (id INTEGER PRIMARY KEY, name TEXT, price REAL, 
                  category TEXT, image_url TEXT, image TEXT)''')
    conn.commit()
    conn.close()

init_db()

@app.route('/uploads/<path:filename>')
def uploaded_files(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

@app.route('/api/products', methods=['GET'])
def get_products():
    conn = get_db()
    products = conn.execute('SELECT * FROM products').fetchall()
    conn.close()
    return jsonify([dict(p) for p in products])

@app.route('/api/products', methods=['POST'])
def add_product():
    name = request.form.get('name')
    price = request.form.get('price')
    category = request.form.get('category','general')
    file = request.files.get('image')
    image_url = ''
    if file:
        filename = secure_filename(file.filename)
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)
        image_url = f"https://ed-parts-shop.onrender.com/uploads/{filename}"
    conn = get_db()
    conn.execute('INSERT INTO products (name,price,category,image_url,image) VALUES (?,?,?,?,?)',
                 (name,price,category,image_url,image_url))
    conn.commit()
    conn.close()
    return jsonify({"success": True, "image_url": image_url})

@app.route('/')
def home():
    return "Ed Parts Shop API Running"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
