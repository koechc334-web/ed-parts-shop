from flask import Flask, request, jsonify, send_from_directory
import os, sqlite3, uuid
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
DB = 'ikokitufiti.db'

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE,
        phone TEXT,
        password_hash TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS listings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        title TEXT,
        price REAL,
        category TEXT,
        description TEXT,
        image_path TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def index():
    return """
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ikokitufiti.co.ke - Western Merchants</title>
<style>
body{font-family:Arial;margin:0;background:#f5f5f5}
.header{background:#b91c1c;color:white;padding:12px;display:flex;justify-content:space-between}
.tabs{display:flex;background:white;overflow-x:auto}
.tab{padding:12px;flex:1;text-align:center;cursor:pointer;white-space:nowrap}
.tab.active{color:#b91c1c;border-bottom:3px solid #b91c1c;font-weight:bold}
.panel{display:none;padding:16px}
.panel.active{display:block}
.card{background:white;padding:16px;border-radius:12px;box-shadow:0 2px 6px rgba(0,0,0,0.1);margin-bottom:12px}
input,textarea,select{width:100%;padding:12px;margin:6px 0;border:1px solid #ddd;border-radius:8px;box-sizing:border-box;font-size:16px}
button{background:#b91c1c;color:white;border:none;padding:12px;border-radius:8px;width:100%;font-size:16px;margin-top:8px}
.listing-img{width:100%;height:180px;object-fit:cover;border-radius:8px;background:#eee;display:flex;align-items:center;justify-content:center;color:#888}
</style>
</head>
<body>
<div class="header"><div><b>ikokitufiti.co.ke - Western Merchants</b></div><div id="userStatus">Guest</div></div>
<div class="tabs">
<div class="tab active" onclick="showTab(0)">Home</div>
<div class="tab" onclick="showTab(1)">Shop</div>
<div class="tab" onclick="showTab(2)">Sell</div>
<div class="tab" onclick="showTab(3)">My Items</div>
<div class="tab" onclick="showTab(4)">Cart</div>
<div class="tab" onclick="showTab(5)">Orders</div>
<div class="tab" onclick="showTab(6)">Account</div>
</div>

<div id="p0" class="panel active"><div class="card"><h2>Welcome to Western Merchants</h2><p>Buy & Sell locally in Kitale, Eldoret, Bungoma. Fast M-Pesa.</p><input id="homeSearch" placeholder="Search tools, spare parts..."><button onclick="doSearch()">Search</button></div><div id="featured"></div></div>

<div id="p1" class="panel"><div class="card"><h3>Shop</h3><input id="shopSearch" placeholder="Search shop..."><button onclick="loadListings()">Search</button></div><div id="shopList"></div></div>

<div id="p2" class="panel"><div class="card"><h3>Sell Item (Like Jiji)</h3>
<input id="sTitle" placeholder="Title e.g. 2HP Water Pump">
<input id="sPrice" type="number" placeholder="Price KES">
<select id="sCategory"><option>Tools</option><option>Spare Parts</option><option>Electronics</option><option>Farm</option><option>Other</option></select>
<textarea id="sDesc" placeholder="Description, location, condition"></textarea>
<input id="sImage" type="file" accept="image/*">
<button onclick="createListing()">Post Now</button><p id="sellMsg"></p></div></div><div id="p3" class="panel"><div id="myItems"></div></div>
<div id="p4" class="panel"><div id="cartItems"></div><div class="card"><b>Total: KES <span id="cartTotal">0</span></b><button onclick="checkout()">Checkout via WhatsApp</button></div></div>
<div id="p5" class="panel"><div id="ordersList"><p>No orders yet</p></div></div>

<div id="p6" class="panel">
<div class="card">
<h3>Create Account</h3>
<input id="rName" placeholder="Full Name">
<input id="rEmail" type="email" placeholder="Email">
<input id="rPhone" placeholder="Phone 07...">
<input id="rPass" type="password" placeholder="Password min 6">
<button onclick="register()">Create Account</button>
<p id="rMsg"></p>
<hr>
<h3>Login</h3>
<input id="lEmail" placeholder="Email">
<input id="lPass" type="password" placeholder="Password">
<button onclick="login()">Login</button>
<p id="lMsg"></p>
</div>
</div>

<script>
let currentUser = JSON.parse(localStorage.getItem('user')||'null');
let cart = JSON.parse(localStorage.getItem('cart')||'[]');
function showTab(i){
 document.querySelectorAll('.tab').forEach((t,idx)=>{t.classList.toggle('active',idx===i)});
 document.querySelectorAll('.panel').forEach((p,idx)=>{p.classList.toggle('active',idx===i)});
 if(i===1) loadListings();
 if(i===3) loadMyItems();
 if(i===4) renderCart();
}
function updateUserUI(){
 document.getElementById('userStatus').innerText = currentUser ? currentUser.email : 'Guest';
}
updateUserUI();
async function loadListings(){
 const q = document.getElementById('shopSearch')?.value || document.getElementById('homeSearch')?.value || '';
 const res = await fetch('/api/listings?q='+encodeURIComponent(q));
 const data = await res.json();
 const html = data.map(l=>{
  let img = l.image_path ? '<img src="/'+l.image_path+'" style="width:100%;height:180px;object-fit:cover;border-radius:8px">' : 'No Image';
  return '<div class="card"><div class="listing-img">'+img+'</div><h4>'+l.title+'</h4><p>KES '+l.price+' - '+l.category+'</p><p>'+(l.description||'').slice(0,100)+'</p><button onclick="addToCart('+l.id+', \''+l.title.replace(/'/g,'')+'\', '+l.price+')">Add to Cart</button><button style="background:green" onclick="buyWhatsApp(\''+l.title.replace(/'/g,'')+'\')">WhatsApp Seller</button></div>';
 }).join('');
 document.getElementById('shopList').innerHTML = html || '<p>No items</p>';
 document.getElementById('featured').innerHTML = html || '';
}
loadListings();
async function register(){
 const body={name:document.getElementById('rName').value,email:document.getElementById('rEmail').value,phone:document.getElementById('rPhone').value,password:document.getElementById('rPass').value};
 const res=await fetch('/api/auth/register',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
 const d=await res.json();
 document.getElementById('rMsg').innerText = d.message || d.error;
 if(res.ok) { alert('Account created! Now login'); showTab(6); }
}
async function login(){
 const body={email:document.getElementById('lEmail').value,password:document.getElementById('lPass').value};
 const res=await fetch('/api/auth/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
 const d=await res.json();
 document.getElementById('lMsg').innerText = d.message || d.error;
 if(res.ok){ currentUser=d.user; localStorage.setItem('user',JSON.stringify(d.user)); updateUserUI(); alert('Logged in'); showTab(1); }
}
async function createListing(){
 if(!currentUser){ alert('Login first'); showTab(6); return; }
 const fd=new FormData();
 fd.append('title',document.getElementById('sTitle').value);
 fd.append('price',document.getElementById('sPrice').value);
 fd.append('category',document.getElementById('sCategory').value);
 fd.append('description',document.getElementById('sDesc').value);
 fd.append('user_id',currentUser.id);
 if(document.getElementById('sImage').files[0]) fd.append('image',document.getElementById('sImage').files[0]);
 const res=await fetch('/api/listings/create',{method:'POST',body:fd});
 const d=await res.json();
 document.getElementById('sellMsg').innerText=d.message||d.error;
 if(res.ok) { alert('Posted!'); loadListings(); showTab(1); }
}
function addToCart(id,title,price){ cart.push({id,title,price}); localStorage.setItem('cart',JSON.stringify(cart)); alert('Added'); renderCart(); }
function renderCart(){
 let total=0;
 document.getElementById('cartItems').innerHTML = cart.map((c,i)=>{ total+=parseFloat(c.price); return '<div class="card">'+c.title+' - KES '+c.price+' <button onclick="removeCart('+i+')">Remove</button></div>' }).join('') || '<p>Cart empty</p>';
 document.getElementById('cartTotal').innerText=total;
}
function removeCart(i){ cart.splice(i,1); localStorage.setItem('cart',JSON.stringify(cart)); renderCart(); }
function doSearch(){ showTab(1); loadListings(); }
function buyWhatsApp(title){ window.open('https://wa.me/254710547481?text=Hi, I am interested in '+encodeURIComponent(title)+' on ikokitufiti','_blank'); }
function checkout(){ if(cart.length===0){ alert('Cart empty'); return; } let msg='Order from ikokitufiti: %0A'+cart.map(c=>c.title+' - KES '+c.price).join('%0A'); window.open('https://wa.me/254710547481?text='+msg,'_blank'); }
async function loadMyItems(){ if(!currentUser) { document.getElementById('myItems').innerHTML='<p>Login to see items</p>'; return; } const res=await fetch('/api/listings?user_id='+currentUser.id); const data=await res.json(); document.getElementById('myItems').innerHTML = data.map(l=>'<div class="card">'+l.title+' - KES '+l.price+'</div>').join('') || '<p>No items</p>'; }
</script>
</body></html>
    """

@app.route('/api/auth/register', methods=['POST'])
def api_register():
    data = request.get_json()
    if not data or not data.get('email') or not data.get('password'):
        return jsonify({"error":"Email and password required"}),400
    if len(data['password']) < 6:
        return jsonify({"error":"Password min 6 chars"}),400
    try:
        conn=get_db()
        conn.execute("INSERT INTO users (email,phone,password_hash) VALUES (?,?,?)",
                     (data['email'], data.get('phone'), generate_password_hash(data['password'])))
        conn.commit()
        conn.close()
        return jsonify({"message":"Account created"}),201
    except Exception as e:
        return jsonify({"error": str(e) + " - maybe email exists"}),400

@app.route('/api/auth/login', methods=['POST'])
def api_login():
    data=request.get_json()
    conn=get_db()
    row=conn.execute("SELECT * FROM users WHERE email=?", (data.get('email'),)).fetchone()
    conn.close()
    if not row or not check_password_hash(row['password_hash'], data.get('password','')):
        return jsonify({"error":"Invalid email or password"}),401
    return jsonify({"message":"Logged in","user":{"id":row['id'],"email":row['email'],"phone":row['phone']}})

@app.route('/api/listings')
def api_listings():
    q=request.args.get('q','')
    uid=request.args.get('user_id')
    conn=get_db()
    if uid:
        rows=conn.execute("SELECT * FROM listings WHERE user_id=? ORDER BY id DESC",(uid,)).fetchall()
    elif q:
        rows=conn.execute("SELECT * FROM listings WHERE title LIKE ? OR description LIKE ? ORDER BY id DESC", ('%'+q+'%','%'+q+'%')).fetchall()
    else:
        rows=conn.execute("SELECT * FROM listings ORDER BY id DESC").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route('/api/listings/create', methods=['POST'])
def api_create():
    title=request.form.get('title')
    price=request.form.get('price')
    category=request.form.get('category')
    desc=request.form.get('description')
    user_id=request.form.get('user_id')
    if not title or not price:
        return jsonify({"error":"Title and price required"}),400
    image_path=''
    if 'image' in request.files:
        f=request.files['image']
        if f.filename:
            os.makedirs('uploads',exist_ok=True)
            fname=str(uuid.uuid4())+'_'+f.filename
            f.save(os.path.join('uploads',fname))
            image_path='uploads/'+fname
    conn=get_db()
    conn.execute("INSERT INTO listings (user_id,title,price,category,description,image_path) VALUES (?,?,?,?,?,?)",
                 (user_id,title,price,category,desc,image_path))
    conn.commit()
    conn.close()
    return jsonify({"message":"Listing created"})

@app.route('/uploads/<path:filename>')
def serve_upload(filename):
    return send_from_directory('uploads', filename)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
