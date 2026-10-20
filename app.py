import os
import re
import json
import uuid
import sqlite3
from flask import Flask, request, jsonify, render_template_string
from flask_bcrypt import Bcrypt
from flask_jwt_extended import (
    JWTManager,
    create_access_token,
    jwt_required,
    get_jwt_identity
)
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config["JWT_SECRET_KEY"] = os.environ.get("JWT_SECRET_KEY", "CHANGE_ME_TO_LONG_RANDOM_SECRET")
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024
app.config["UPLOAD_FOLDER"] = os.environ.get("UPLOAD_FOLDER", "uploads")
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

bcrypt = Bcrypt(app)
jwt = JWTManager(app)
DB_NAME = os.environ.get("DB_NAME", "western_merchants.db")

PART_KEYWORDS = [
    "tire","tyre","wheel","rim","door","mirror","headlight","taillight",
    "battery","brake","brake pad","spark plug","engine","gearbox","transmission",
    "bumper","hood","bonnet","trunk","radiator","starter","alternator","filter",
    "air filter","oil filter","wiper","windshield","seat","door panel","axle"
]

def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute("""
    CREATE TABLE IF NOT EXISTS users (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      email TEXT UNIQUE NOT NULL,
      pwd_hash TEXT NOT NULL,
      phone TEXT,
      created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS listings (
      id TEXT PRIMARY KEY,
      user_email TEXT NOT NULL,
      title TEXT NOT NULL,
      description TEXT,
      price REAL NOT NULL,
      category TEXT,
      image_path TEXT,
      status TEXT NOT NULL DEFAULT 'active',
      created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS parts (
      id TEXT PRIMARY KEY,
      listing_id TEXT NOT NULL,
      name TEXT NOT NULL,
      description TEXT,
      price REAL NOT NULL,
      qty INTEGER NOT NULL DEFAULT 1,
      condition TEXT,
      image_path TEXT,
      seller_email TEXT,
      status TEXT DEFAULT 'available',
      created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS orders (
      id TEXT PRIMARY KEY,
      email TEXT NOT NULL,
      items TEXT NOT NULL,
      total REAL NOT NULL,
      status TEXT NOT NULL DEFAULT 'pending',
      delivery_address TEXT,
      delivery_fee REAL DEFAULT 0,
      created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS payments (
      id TEXT PRIMARY KEY,
      order_id TEXT NOT NULL,
      email TEXT NOT NULL,
      amount REAL NOT NULL,
      phone TEXT NOT NULL,
      status TEXT NOT NULL DEFAULT 'pending',
      created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """)
    conn.commit()
    conn.close()

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in {"png","jpg","jpeg","gif","webp"}

def valid_email(email):
    return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email))

def valid_password(pwd):
    return bool(re.match(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).{8,}$", pwd))

def extract_parts_from_text(title, description):
    text = (title + " " + description).lower()
    found = {}
    for kw in PART_KEYWORDS:
        if kw in text:
            found[kw] = found.get(kw, 0) + 1
    return [
        {"name": k.title(), "suggested_qty": v, "suggested_price": None}
        for k, v in found.items()
    ]

HTML_PAGE = """
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>ikokitufiti.co.ke — Western Merchants</title>
  <style>
    :root{
      --primary:#b91c1c;
      --accent:#f59e0b;
      --bg:#fff5f5;
      --card:#fff;
      --muted:#6b7280;
      --shadow:0 4px 18px rgba(185,28,28,0.08);
    }
    *{box-sizing:border-box}
    body{margin:0;padding:0;background:var(--bg);font-family:system-ui,sans-serif;color:#111}
    header{
      background:var(--primary);
      color:#fff;
      padding:14px 18px;
      display:flex;
      justify-content:space-between;
      align-items:center;
      position:sticky; top:0; z-index:20;
    }
    .brand{font-weight:900}
    #user{background:rgba(255,255,255,0.12);padding:6px 10px;border-radius:999px}
    .tabs{display:flex;overflow-x:auto;background:#fff;box-shadow:var(--shadow);position:sticky;top:56px;z-index:10}
    .tab{padding:12px 14px;cursor:pointer;border-bottom:3px solid transparent;min-width:90px;text-align:center;font-weight:800;color:var(--muted)}
    .tab.active{border-color:var(--primary);color:var(--primary);background:#fff7f7}
    .panel{display:none;max-width:980px;margin:20px auto;padding:0 16px 40px}
    .panel.active{display:block}
    .card{background:#fff;border-radius:12px;padding:16px;margin:12px 0;box-shadow:var(--shadow)}
    input, textarea, select, button{
      width:100%;
      margin:8px 0;
      padding:10px 12px;
      border-radius:8px;
      border:1px solid #f0d8d8;
      font:inherit;
    }
    textarea{min-height:100px}
    button{
      background:var(--primary);
      color:#fff;
      border:none;
      cursor:pointer;
      font-weight:900;
    }
    button.secondary{
      background:#fff;
      color:var(--primary);
      border:1px solid var(--primary);
    }
    .upload-box{
      border:2px dashed #f0d8d8;
      background:#fff7f7;
      border-radius:10px;
      padding:14px;
      text-align:center;
      cursor:pointer;
    }
    .listings-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:12px}
    .listing-card{background:#fff;border-radius:10px;padding:0;overflow:hidden;box-shadow:var(--shadow)}
    .listing-image{width:100%;height:150px;object-fit:cover;background:#fee2e2}
    .listing-info{padding:12px}
    .listing-price{font-weight:900}
    .cart-item{display:flex;justify-content:space-between;align-items:center;padding:10px 0;border-bottom:1px solid #f7e6e6}
    .order-card{background:#fff;border-radius:10px;padding:12px;margin:8px 0}
    .hint{font-size:13px;color:var(--muted)}
    .info{background:#fff7f7;padding:10px;border-radius:8px;border:1px solid #f8d9d9}
    .parts-list{display:grid;gap:8px;margin-top:8px}
    .part-card{background:#fff;border:1px solid #f7e6e6;border-radius:8px;padding:8px;display:flex;justify-content:space-between;align-items:center}
    @media (max-width:640px){ .tabs{font-size:12px} .tab{min-width:80px} }
  </style>
</head>
<body>
  <header>
    <div class="brand">ikokitufiti.co.ke — Western Merchants</div>
    <div id="user">Guest</div>
  </header>

  <div class="tabs">
    <div class="tab active" data-tab="0">Home</div>
    <div class="tab" data-tab="1">Shop</div>
    <div class="tab" data-tab="2">Sell</div>
    <div class="tab" data-tab="3">My Items</div>
    <div class="tab" data-tab="4">Cart</div>
    <div class="tab" data-tab="5">Orders</div>
    <div class="tab" data-tab="6">Track</div>
    <div class="tab" data-tab="7">Account</div>
  </div>

  <div class="panel active" id="p0">
    <div class="card">
      <h2>Welcome to ikokitufiti.co.ke</h2>
      <p class="hint">Sell spare parts, full vehicles, or split listings into individual components.</p>
    </div>
    <div class="card">
      <h3>Platform stats</h3>
      <div id="stats" class="info">Loading...</div>
    </div>
  </div>

  <div class="panel" id="p1">
    <div class="card">
      <h3>Shop</h3>
      <div id="listings" class="listings-grid"></div>
    </div>
  </div>

  <div class="panel" id="p2">
    <div class="card">
      <h3>Sell</h3>
      <input id="sellTitle" placeholder="Title (e.g. Toyota Corolla for spares)">
      <textarea id="sellDesc" placeholder="Describe the item or vehicle"></textarea>
      <input id="sellPrice" type="number" placeholder="Price (KSh)">
      <select id="sellCategory">
        <option>Vehicles</option>
        <option>Brake</option>
        <option>Engine</option>
        <option>Lighting</option>
        <option>Accessories</option>
        <option>Other</option>
      </select>

      <div class="upload-box" onclick="document.getElementById('photoInput').click()">
        <div>📷 Upload clear photo</div>
        <div class="hint">Phone camera or gallery</div>
        <input id="photoInput" type="file" accept="image/*" capture="environment" onchange="previewSellPhoto()">
      </div>
      <img id="sellPreview" style="display:none;max-width:100%;margin-top:10px;border-radius:8px">

      <div style="display:flex;gap:8px;margin-top:10px">
        <button onclick="suggestParts()">Suggest Parts</button>
        <button onclick="createListing()">Create Listing</button>
      </div>

      <div id="partSuggestions" style="margin-top:12px"></div>
    </div>
  </div>

  <div class="panel" id="p3">
    <div class="card">
      <h3>My Items</h3>
      <div id="myListings"></div>
    </div>
  </div>

  <div class="panel" id="p4">
    <div class="card">
      <h3>Cart</h3>
      <div id="cart"></div>
      <div id="cartActions" style="display:none;margin-top:12px">
        <input id="deliveryAddress" placeholder="Delivery address">
        <button onclick="calculateDelivery()">Calculate Delivery</button>
        <div id="deliveryInfo"></div>
        <button onclick="checkout()">Checkout</button>
      </div>
    </div>
  </div>

  <div class="panel" id="p5">
    <div class="card">
      <h3>Orders</h3>
      <div id="orders"></div>
    </div>
  </div>

  <div class="panel" id="p6">
    <div class="card">
      <h3>Track Order</h3>
      <input id="trackId" placeholder="Order ID">
      <button onclick="trackOrder()">Track</button>
      <div id="trackResult" style="margin-top:12px"></div>
    </div>
  </div>

  <div class="panel" id="p7">
    <div class="card" id="authCard">
      <h3>Account</h3>
      <input id="email" type="email" placeholder="Email">
      <input id="phone" type="tel" placeholder="Phone (254...)">
      <input id="pwd" type="password" placeholder="Password (8+ chars, upper/lower/number)">
      <button onclick="register()">Create account</button>
      <div style="text-align:center;margin-top:12px">
        <a href="#" onclick="showLogin(); return false;">Already have account? Login</a>
      </div>
    </div>
  </div>

  <script>
    const state = {
      token: localStorage.getItem('token') || '',
      user: localStorage.getItem('user') || '',
      cart: JSON.parse(localStorage.getItem('cart') || '[]'),
      listings: [],
      myListings: []
    };

    function api(path, opts = {}) {
      opts.headers = opts.headers || {};
      if (state.token) opts.headers['Authorization'] = 'Bearer ' + state.token;
      return fetch(path, opts).then(r => r.json().then(j => ({ ok: r.ok, status: r.status, body: j })));
    }

    document.querySelectorAll('.tab').forEach(tab => {
      tab.onclick = () => {
        const index = Number(tab.dataset.tab);
        document.querySelectorAll('.tab').forEach(t => t.classList.toggle('active', t === tab));
        document.querySelectorAll('.panel').forEach((p, i) => p.classList.toggle('active', i === index));
        if (index === 1) loadListings();
        if (index === 3) loadMyListings();
        if (index === 5) loadOrders();
      };
    });

    function updateUserUI() {
      const userEl = document.getElementById('user');
      userEl.innerText = state.user ? state.user.split('@')[0] + ' ✅' : 'Guest';
    }

    function previewSellPhoto() {
      const input = document.getElementById('photoInput');
      const img = document.getElementById('sellPreview');
      if (input.files && input.files[0]) {
        const reader = new FileReader();
        reader.onload = e => { img.src = e.target.result; img.style.display = 'block'; };
        reader.readAsDataURL(input.files[0]);
      }
    }

    async function register() {
      const email = document.getElementById('email').value.trim().toLowerCase();
      const phone = document.getElementById('phone').value.trim();
      const pwd = document.getElementById('pwd').value;
      if (!email || !phone || !pwd) {
        alert('All fields are required');
        return;
      }
      const res = await api('/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, phone, password: pwd })
      });
      if (res.ok) {
        state.user = res.body.user;
        state.token = res.body.token;
        localStorage.setItem('token', state.token);
        localStorage.setItem('user', state.user);
        updateUserUI();
        alert('Account created');
        showTab(0);
      } else {
        alert(res.body.error || 'Register failed');
      }
    }

    function showLogin() {
      document.getElementById('authCard').innerHTML = `
        <h3>Login</h3>
        <input id='loginEmail' type='email' placeholder='Email'>
        <input id='loginPwd' type='password' placeholder='Password'>
        <button onclick='login()'>Login</button>
        <div style='text-align:center;margin-top:10px'>
          <a href='#' onclick='location.reload();'>Register</a>
        </div>
      `;
    }

    async function login() {
      const email = document.getElementById('loginEmail').value.trim().toLowerCase();
      const pwd = document.getElementById('loginPwd').value;
      const res = await api('/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password: pwd })
      });
      if (res.ok) {
        state.user = res.body.user;
        state.token = res.body.token;
        localStorage.setItem('token', state.token);
        localStorage.setItem('user', state.user);
        updateUserUI();
        alert('Login successful');
        showTab(0);
      } else {
        alert(res.body.error || 'Login failed');
      }
    }

    function showTab(index) {
      document.querySelectorAll('.tab').forEach((t, i) => t.classList.toggle('active', i === index));
      document.querySelectorAll('.panel').forEach((p, i) => p.classList.toggle('active', i === index));
      if (index === 1) loadListings();
      if (index === 3) loadMyListings();
      if (index === 5) loadOrders();
    }

    async function loadListings() {
      const res = await api('/api/listings');
      const listingsEl = document.getElementById('listings');
      if (!res.ok) {
        listingsEl.innerHTML = '<div class=\"card\">Unable to load listings</div>';
        return;
      }
      state.listings = res.body.listings || [];
      if (!state.listings.length) {
        listingsEl.innerHTML = '<div class=\"card\">No listings yet.</div>';
        return;
      }
      listingsEl.innerHTML = state.listings.map(l => `
        <div class="listing-card">
          ${l.image_path ? `<img class="listing-image" src="${l.image_path}" alt="${l.title}" />` : `<div class="listing-image" style="display:flex;align-items:center;justify-content:center;color:#666">No image</div>`}
          <div class="listing-info">
            <h4>${l.title}</h4>
            <div class="listing-price">KSh ${l.price}</div>
            <div class="hint">${l.category || 'Other'} • ${l.user_email ? l.user_email.split('@')[0] : 'seller'}</div>
            <div style="display:flex;gap:8px;margin-top:8px">
              <button class="secondary" onclick="addToCart({id: '${l.id}', title: '${l.title}', price: ${l.price}, qty: 1})">Add</button>
            </div>
            <div id="parts_${l.id}" style="margin-top:8px"></div>
          </div>
        </div>
      `).join('');

      for (const l of state.listings) {
        const partRes = await api(`/api/listings/${l.id}/parts`);
        const partsEl = document.getElementById(`parts_${l.id}`);
        if (!partsEl) continue;
        if (partRes.ok && partRes.body.parts && partRes.body.parts.length) {
          partsEl.innerHTML = `<div class="parts-list">` + partRes.body.parts.map(p => `
            <div class="part-card">
              <div>
                <strong>${p.name}</strong><br>
                <span class="hint">KSh ${p.price} • Qty ${p.qty}</span>
              </div>
              <button class="secondary" onclick="addToCart({id:'${p.id}', title:'${p.name}', price:${p.price}, qty:1})" style="width:90px;padding:7px">Add</button>
            </div>
          `).join('') + `</div>`;
        } else {
          partsEl.innerHTML = '';
        }
      }
    }

    async function suggestParts() {
      const title = document.getElementById('sellTitle').value.trim();
      const description = document.getElementById('sellDesc').value.trim();
      const res = await api('/api/suggest_parts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title, description })
      });
      const box = document.getElementById('partSuggestions');
      if (!res.ok || !res.body.suggestions.length) {
        box.innerHTML = '<div class=\"info\">No suggestions found</div>';
        return;
      }
      box.innerHTML = res.body.suggestions.map((s, idx) => `
        <div class="card" style="padding:10px">
          <div style="display:flex;gap:8px;align-items:center">
            <input id="s_name_${idx}" value="${s.name}" style="flex:1">
            <input id="s_qty_${idx}" type="number" value="${s.suggested_qty}" style="width:80px">
            <input id="s_price_${idx}" type="number" placeholder="Price" style="width:120px">
            <button onclick="createSuggestedPart(${idx})">Create</button>
          </div>
        </div>
      `).join('');
      window.__suggestions = res.body.suggestions;
    }

    async function createListing() {
      const title = document.getElementById('sellTitle').value.trim();
      const description = document.getElementById('sellDesc').value.trim();
      const price = document.getElementById('sellPrice').value;
      const category = document.getElementById('sellCategory').value;
      const file = document.getElementById('photoInput').files[0];

      if (!state.token) {
        alert('Login required'); showTab(7); return;
      }
      if (!title || !price) {
        alert('Title and price required'); return;
      }

      const form = new FormData();
      form.append("title", title);
      form.append("description", description);
      form.append("price", price);
      form.append("category", category);
      if (file) form.append("file", file);

      const res = await fetch('/api/listings', {
        method: 'POST',
        headers: { 'Authorization': 'Bearer ' + state.token },
        body: form
      });
      const json = await res.json();
      if (!res.ok) {
        alert(json.error || 'Error creating listing');
        return;
      }

      document.getElementById('sellTitle').value = '';
      document.getElementById('sellDesc').value = '';
      document.getElementById('sellPrice').value = '';
      document.getElementById('photoInput').value = '';
      document.getElementById('sellPreview').style.display = 'none';
      document.getElementById('partSuggestions').innerHTML = '';
      loadListings();
      loadMyListings();
      alert('Listing created');
    }

    async function createSuggestedPart(index) {
      if (!state.token) { alert('Login required'); return; }
      const name = document.getElementById(`s_name_${index}`).value.trim();
      const qty = parseInt(document.getElementById(`s_qty_${index}`).value || 1);
      const price = parseFloat(document.getElementById(`s_price_${index}`).value || 0);

      if (!name || !price) { alert('Name and price required'); return; }

      const title = document.getElementById('sellTitle').value.trim() || name;
      const description = document.getElementById('sellDesc').value.trim();
      const form = new FormData();
      form.append("title", title);
      form.append("description", description);
      form.append("price", document.getElementById('sellPrice').value || price);
      form.append("category", document.getElementById('sellCategory').value || 'Other');
      if (document.getElementById('photoInput').files[0]) form.append("file", document.getElementById('photoInput').files[0]);

      const createRes = await fetch('/api/listings', {
        method: 'POST',
        headers: { 'Authorization': 'Bearer ' + state.token },
        body: form
      });
      const createdJson = await createRes.json();
      if (!createRes.ok) {
        alert(createdJson.error || 'Unable to create parent listing');
        return;
      }
      const listingId = createdJson.listing_id;

      const partRes = await api(`/api/listings/${listingId}/parts`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + state.token },
        body: JSON.stringify({
          name,
          description: description || 'Suggested part',
          price,
          qty,
          condition: 'used'
        })
      });
      if (partRes.ok) {
        alert('Suggested part created');
        loadListings();
        loadMyListings();
      } else {
        alert(partRes.body.error || 'Unable to create part');
      }
    }

    async function loadMyListings() {
      const target = document.getElementById('myListings');
      if (!state.token) {
        target.innerHTML = '<div class=\"card\">Login to see your listings.</div>';
        return;
      }
      const res = await api('/api/my-listings');
      if (!res.ok) {
        target.innerHTML = '<div class=\"card\">Unable to load listings</div>';
        return;
      }
      const listings = res.body.listings || [];
      if (!listings.length) {
        target.innerHTML = '<div class=\"card\">No listings yet</div>';
        return;
      }
      target.innerHTML = listings.map(l => `
        <div class="order-card">
          <div style="display:flex;gap:10px">
            ${l.image_path ? `<img src="${l.image_path}" style="width:90px;height:70px;object-fit:cover;border-radius:8px">` : `<div style="width:90px;height:70px;background:#fee;border-radius:8px"></div>`}
            <div style="flex:1">
              <strong>${l.title}</strong>
              <div class="hint">${l.description || ''}</div>
              <div>KSh ${l.price}</div>
              <div style="display:flex;gap:8px;margin-top:8px">
                <button onclick="deleteListing('${l.id}')">Delete</button>
              </div>
            </div>
          </div>
        </div>
      `).join('');
    }

    async function deleteListing(id) {
      const res = await api(`/api/listings/${id}`, { method: 'DELETE' });
      if (res.ok) {
        alert('Listing deleted');
        loadListings();
        loadMyListings();
      } else {
        alert(res.body.error || 'Delete failed');
      }
    }

    function addToCart(item) {
      state.cart.push(item);
      localStorage.setItem('cart', JSON.stringify(state.cart));
      renderCart();
      alert('Added to cart');
    }

    function removeCart(index) {
      state.cart.splice(index, 1);
      localStorage.setItem('cart', JSON.stringify(state.cart));
      renderCart();
    }

    function renderCart() {
      const cartEl = document.getElementById('cart');
      const actions = document.getElementById('cartActions');
      if (!state.cart.length) {
        cartEl.innerHTML = '<div class=\"card\">Your cart is empty</div>';
        actions.style.display = 'none';
        return;
      }
      const total = state.cart.reduce((sum, item) => sum + Number(item.price || 0), 0);
      cartEl.innerHTML = state.cart.map((item, index) => `
        <div class="cart-item">
          <div>${item.title}</div>
          <div>KSh ${item.price} <button class="secondary" onclick="removeCart(${index})" style="width:70px;padding:7px;margin-left:8px">Remove</button></div>
        </div>
      `).join('') + `<div class=\"card\">Subtotal: KSh ${total}</div>`;
      actions.style.display = 'block';
    }

    async function calculateDelivery() {
      const address = document.getElementById('deliveryAddress').value.trim();
      if (!address) {
        alert('Enter delivery address');
        return;
      }
      const res = await fetch('/api/delivery/distance', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ origin: 'Eldoret', destination: address })
      });
      const data = await res.json();
      if (!res.ok) {
        alert(data.error || 'Delivery failed');
        return;
      }
      state.deliveryFee = data.delivery_fee || 500;
      const total = state.cart.reduce((s, i) => s + Number(i.price || 0), 0) + state.deliveryFee;
      document.getElementById('deliveryInfo').innerHTML = `<div class=\"info\">Distance: ${data.distance} • Duration: ${data.duration} • Delivery fee: KSh ${data.delivery_fee} • Total: KSh ${total}</div>`;
    }

    async function checkout() {
      if (!state.token) {
        alert('Login required'); showTab(7); return;
      }
      if (!state.cart.length) {
        alert('Cart is empty'); return;
      }
      const total = state.cart.reduce((s, i) => s + Number(i.price || 0), 0) + (state.deliveryFee || 0);
      const payload = {
        items: state.cart,
        delivery_address: document.getElementById('deliveryAddress').value.trim(),
        delivery_fee: state.deliveryFee || 0
      };
      const res = await api('/api/order', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (!res.ok) {
        alert(res.body.error || 'Checkout failed');
        return;
      }
      const orderId = res.body.order_id;
      const message = `Hello, I want to pay for order ${orderId}. Total KSh ${res.body.total}. Items: ${state.cart.map(i => i.title).join(', ')}`;
      window.open(`https://wa.me/2547XXXXXXXX?text=${encodeURIComponent(message)}`, '_blank');
      state.cart = [];
      localStorage.setItem('cart', JSON.stringify(state.cart));
      renderCart();
      alert('Order created: ' + orderId);
      showTab(5);
    }

    async function loadOrders() {
      const ordersEl = document.getElementById('orders');
      if (!state.token) {
        ordersEl.innerHTML = '<div class=\"card\">Login to view orders</div>';
        return;
      }
      const res = await api('/api/orders');
      if (!res.ok) {
        ordersEl.innerHTML = '<div class=\"card\">Unable to load orders</div>';
        return;
      }
      const orders = res.body.orders || [];
      if (!orders.length) {
        ordersEl.innerHTML = '<div class=\"card\">No orders yet</div>';
        return;
      }
      ordersEl.innerHTML = orders.map(o => `
        <div class="order-card">
          <div style="display:flex;justify-content:space-between">
            <strong>${o.id}</strong>
            <span>${o.status}</span>
          </div>
          <div>KSh ${o.total}</div>
          <div class="hint">${o.created_at}</div>
        </div>
      `).join('');
    }

    async function trackOrder() {
      const id = document.getElementById('trackId').value.trim();
      if (!id) { alert('Enter order ID'); return; }
      const res = await fetch('/api/track/' + encodeURIComponent(id));
      const data = await res.json();
      if (!res.ok) {
        document.getElementById('trackResult').innerHTML = '<div class=\"info\">Order not found</div>';
        return;
      }
      document.getElementById('trackResult').innerHTML = `
        <div class="order-card">
          <strong>Order: ${data.id}</strong>
          <div>Status: ${data.status}</div>
          <div>Total: KSh ${data.total}</div>
          <div>Items: ${JSON.parse(data.items).map(x => x.title).join(', ')}</div>
        </div>
      `;
    }

    async function loadStats() {
      const res = await fetch('/api/stats');
      const data = await res.json();
      document.getElementById('stats').innerHTML = `
        Users: ${data.total_users} • Listings: ${data.total_listings} • Parts: ${data.total_parts} • Orders: ${data.total_orders}
      `;
    }

    updateUserUI();
    renderCart();
    loadListings();
    loadMyListings();
    loadStats();
  </script>
</body>
</html>
"""

@app.route("/")
def home():
    return render_template_string(HTML_PAGE)

# --- API endpoints ---
@app.route("/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    phone = (data.get("phone") or "").strip()
    if not email or not password:
        return jsonify({"error":"Email and password required"}), 400
    if not valid_email(email):
        return jsonify({"error":"Invalid email"}), 400
    if not valid_password(password):
        return jsonify({"error":"Password must be 8+ chars and include uppercase, lowercase and number"}), 400
    hashed = bcrypt.generate_password_hash(password).decode("utf-8")
    conn = get_db()
    try:
        conn.execute("INSERT INTO users (email, pwd_hash, phone) VALUES (?, ?, ?)", (email, hashed, phone))
        conn.commit()
    except sqlite3.IntegrityError:
        return jsonify({"error":"Email already exists"}), 409
    finally:
        conn.close()
    token = create_access_token(identity=email)
    return jsonify({"token": token, "user": email}), 201

@app.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    if not email or not password:
        return jsonify({"error":"Email and password required"}), 400
    conn = get_db()
    row = conn.execute("SELECT pwd_hash FROM users WHERE email = ?", (email,)).fetchone()
    conn.close()
    if not row or not bcrypt.check_password_hash(row["pwd_hash"], password):
        return jsonify({"error":"Invalid credentials"}), 401
    token = create_access_token(identity=email)
    return jsonify({"token": token, "user": email}), 200

@app.route("/api/listings", methods=["GET"])
def get_listings():
    conn = get_db()
    rows = conn.execute("SELECT * FROM listings WHERE status = 'active' ORDER BY created_at DESC").fetchall()
    conn.close()
    return jsonify({"listings": [dict(r) for r in rows]}), 200

@app.route("/api/listings", methods=["POST"])
@jwt_required()
def create_listing():
    user = get_jwt_identity()
    if "file" not in request.files:
        return jsonify({"error":"Image file required"}), 400
    file = request.files["file"]
    title = request.form.get("title","").strip()
    description = request.form.get("description","").strip()
    price = request.form.get("price","0").strip()
    category = request.form.get("category","Other").strip()
    if not title or not price:
        return jsonify({"error":"Title and price required"}), 400
    try:
        price = float(price)
    except:
        return jsonify({"error":"Invalid price"}), 400
    if file.filename == "" or not allowed_file(file.filename):
        return jsonify({"error":"Valid image required"}), 400
    filename = secure_filename(f"{uuid.uuid4().hex}_{file.filename}")
    path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(path)

    listing_id = f"LIST-{uuid.uuid4().hex[:8].upper()}"
    conn = get_db()
    conn.execute("""
        INSERT INTO listings (id, user_email, title, description, price, category, image_path)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (listing_id, user, title, description, price, category, f"/uploads/{filename}"))
    conn.commit()
    conn.close()
    return jsonify({"listing_id": listing_id, "title": title, "price": price, "image": f"/uploads/{filename}", "part_suggestions": extract_parts_from_text(title, description)}), 201

@app.route("/api/my-listings", methods=["GET"])
@jwt_required()
def get_my_listings():
    user = get_jwt_identity()
    conn = get_db()
    rows = conn.execute("SELECT * FROM listings WHERE user_email = ? ORDER BY created_at DESC", (user,)).fetchall()
    conn.close()
    return jsonify({"listings": [dict(r) for r in rows]}), 200

@app.route("/api/listings/<listing_id>", methods=["DELETE"])
@jwt_required()
def delete_listing(listing_id):
    user = get_jwt_identity()
    conn = get_db()
    row = conn.execute("SELECT * FROM listings WHERE id = ?", (listing_id,)).fetchone()
    if not row:
        conn.close()
        return jsonify({"error":"Listing not found"}), 404
    if row["user_email"] != user:
        conn.close()
        return jsonify({"error":"Unauthorized"}), 403
    if row["image_path"]:
        try:
            os.remove(row["image_path"].lstrip("/"))
        except:
            pass
    conn.execute("DELETE FROM listings WHERE id = ?", (listing_id,))
    conn.commit()
    conn.close()
    return jsonify({"status":"deleted"}), 200

@app.route("/api/listings/<listing_id>/parts", methods=["GET"])
def list_parts(listing_id):
    conn = get_db()
    rows = conn.execute("SELECT * FROM parts WHERE listing_id = ? AND status = 'available' ORDER BY created_at DESC", (listing_id,)).fetchall()
    conn.close()
    return jsonify({"parts": [dict(r) for r in rows]}), 200

@app.route("/api/listings/<listing_id>/parts", methods=["POST"])
@jwt_required()
def create_part(listing_id):
    user = get_jwt_identity()
    conn = get_db()
    listing = conn.execute("SELECT * FROM listings WHERE id = ?", (listing_id,)).fetchone()
    if not listing:
        conn.close()
        return jsonify({"error":"Listing not found"}), 404
    if listing["user_email"] != user:
        conn.close()
        return jsonify({"error":"Unauthorized"}), 403

    name = request.form.get("name") or (request.json or {}).get("name")
    description = request.form.get("description") or (request.json or {}).get("description", "")
    price = request.form.get("price") or (request.json or {}).get("price")
    qty = request.form.get("qty") or (request.json or {}).get("qty", 1)
    condition = request.form.get("condition") or (request.json or {}).get("condition", "used")

    if not name or not price:
        conn.close()
        return jsonify({"error":"Name and price required"}), 400
    try:
        price = float(price)
        qty = int(qty)
    except:
        conn.close()
        return jsonify({"error":"Invalid numeric values"}), 400

    image_path = None
    if "file" in request.files:
        f = request.files["file"]
        if f and allowed_file(f.filename):
            filename = secure_filename(f"{uuid.uuid4().hex}_{f.filename}")
            f.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
            image_path = f"/uploads/{filename}"

    part_id = f"PART-{uuid.uuid4().hex[:8].upper()}"
    conn.execute("""
        INSERT INTO parts (id, listing_id, name, description, price, qty, condition, image_path, seller_email)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (part_id, listing_id, name, description, price, qty, condition, image_path, user))
    conn.commit()
    conn.close()
    return jsonify({"part_id": part_id, "name": name, "price": price, "qty": qty}), 201

@app.route("/api/parts/<part_id>/purchase", methods=["POST"])
@jwt_required()
def purchase_part(part_id):
    buyer = get_jwt_identity()
    data = request.get_json(silent=True) or {}
    qty = int(data.get("qty", 1))
    conn = get_db()
    part = conn.execute("SELECT * FROM parts WHERE id = ? AND status = 'available'", (part_id,)).fetchone()
    if not part:
        conn.close()
        return jsonify({"error":"Part not available"}), 404
    if part["qty"] < qty:
        conn.close()
        return jsonify({"error":"Insufficient quantity"}), 400
    total = round(part["price"] * qty, 2)
    order_id = f"ED-{uuid.uuid4().hex[:8].upper()}"
    items = [{ "type":"part", "id":part_id, "title":part["name"], "price":part["price"], "qty":qty }]
    conn.execute("INSERT INTO orders (id, email, items, total, status) VALUES (?, ?, ?, ?, 'pending')", (order_id, buyer, json.dumps(items), total))
    new_qty = part["qty"] - qty
    if new_qty <= 0:
        conn.execute("UPDATE parts SET qty = 0, status = 'sold' WHERE id = ?", (part_id,))
    else:
        conn.execute("UPDATE parts SET qty = ? WHERE id = ?", (new_qty, part_id))
    conn.commit()
    conn.close()
    return jsonify({"order_id": order_id, "total": total, "message":"Part ordered"}), 201

@app.route("/api/suggest_parts", methods=["POST"])
def suggest_parts():
    data = request.get_json(silent=True) or {}
    title = data.get("title","")
    description = data.get("description","")
    return jsonify({"suggestions": extract_parts_from_text(title, description)}), 200

@app.route("/api/order", methods=["POST"])
@jwt_required()
def create_order():
    user = get_jwt_identity()
    data = request.get_json(silent=True) or {}
    items = data.get("items") or []
    if not isinstance(items, list) or not items:
        return jsonify({"error":"Cart is empty"}), 400
    total = 0.0
    for item in items:
        total += float(item.get("price", 0)) * int(item.get("qty", 1))
    delivery_fee = float(data.get("delivery_fee", 0) or 0)
    order_id = f"ED-{uuid.uuid4().hex[:8].upper()}"
    conn = get_db()
    conn.execute("INSERT INTO orders (id, email, items, total, status, delivery_address, delivery_fee) VALUES (?, ?, ?, ?, 'pending', ?, ?)",
                 (order_id, user, json.dumps(items), round(total + delivery_fee, 2), data.get("delivery_address",""), delivery_fee))
    conn.commit()
    conn.close()
    return jsonify({"order_id": order_id, "total": round(total + delivery_fee, 2), "status":"pending"}), 201

@app.route("/api/orders", methods=["GET"])
@jwt_required()
def my_orders():
    user = get_jwt_identity()
    conn = get_db()
    rows = conn.execute("SELECT * FROM orders WHERE email = ? ORDER BY created_at DESC", (user,)).fetchall()
    conn.close()
    return jsonify({"orders":[dict(r) for r in rows]}), 200

@app.route("/api/track/<order_id>", methods=["GET"])
def track(order_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
    conn.close()
    if not row:
        return jsonify({"error":"Order not found"}), 404
    d = dict(row)
    d["items"] = json.loads(d["items"])
    return jsonify(d), 200

@app.route("/api/delivery/distance", methods=["POST"])
def delivery_distance():
    data = request.get_json(silent=True) or {}
    return jsonify({
        "distance": "120 km",
        "duration": "2 hours",
        "delivery_fee": 500
    }), 200

@app.route("/api/payment/mpesa", methods=["POST"])
@jwt_required()
def mock_mpesa():
    data = request.get_json(silent=True) or {}
    phone = data.get("phone")
    amount = data.get("amount")
    order_id = data.get("order_id")
    if not phone or not amount or not order_id:
        return jsonify({"error":"phone, amount and order_id required"}), 400
    payment_id = f"PAY-{uuid.uuid4().hex[:8].upper()}"
    conn = get_db()
    conn.execute("INSERT INTO payments (id, order_id, email, amount, phone, status) VALUES (?, ?, ?, ?, ?, 'initiated')",
                 (payment_id, order_id, get_jwt_identity(), amount, phone))
    conn.commit()
    conn.close()
    return jsonify({"payment_id": payment_id, "status":"initiated", "message":"M-Pesa prompt (mock)"}), 200

@app.route("/api/stats", methods=["GET"])
def stats():
    conn = get_db()
    total_users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    total_listings = conn.execute("SELECT COUNT(*) FROM listings WHERE status='active'").fetchone()[0]
    total_parts = conn.execute("SELECT COUNT(*) FROM parts WHERE status='available'").fetchone()[0]
    total_orders = conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
    conn.close()
    return jsonify({
        "total_users": total_users,
        "total_listings": total_listings,
        "total_parts": total_parts,
        "total_orders": total_orders
    }), 200

init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
