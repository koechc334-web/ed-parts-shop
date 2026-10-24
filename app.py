from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
import secrets
import time
import datetime
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
<div id="authModal">
  <input id="authName" placeholder="Full Name (for signup)">
  <input id="authEmail" placeholder="Email" type="email">
  <div style="position:relative">
    <input id="authPass" placeholder="Password" type="password">
    <span onclick="togglePass()" style="position:absolute; right:10px; top:8px; cursor:pointer">👁️</span>
  </div>
  <button onclick="handleLogin()">Login</button>
  <button onclick="handleRegister()">Create Account</button>
  <a onclick="handleForgot()">Forgot password?</a>
  <p id="authMsg"></p>
</div>

<script>
function togglePass(){
  const p = document.getElementById('authPass');
  p.type = p.type==='password' ? 'text' : 'password';
}
async function handleRegister(){
  const res = await fetch('https://ed-parts-shop.onrender.com/api/register', {
    method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({
      name: authName.value,
      email: authEmail.value,
      password: authPass.value
    })
  });
  const data = await res.json();
  authMsg.innerText = data.message || data.error;
}
async function handleLogin(){ /* same but /api/login */ }
async function handleForgot(){
  const res = await fetch('https://ed-parts-shop.onrender.com/api/forgot-password', {
    method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({email: authEmail.value})
  });
  const data = await res.json();
  authMsg.innerText = data.message + (data.reset_link ? ' Check console' : '');
  // Later: send via email using EmailJS or SMS via Africa's Talking
}
</script>
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
