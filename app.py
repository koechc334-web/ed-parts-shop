<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Create Account - Ikokitufitii</title>
<style>
body{font-family:Roboto,Arial; background:#f5f5f5; margin:0}
.top{background:#000; color:#fff; padding:12px; text-align:center; font-weight:bold}
.container{max-width:400px; margin:20px auto; background:#fff; padding:25px; border-radius:8px; box-shadow:0 2px 10px #ddd}
input{width:100%; padding:12px; margin:8px 0; border:1px solid #ccc; border-radius:5px; box-sizing:border-box}
.pass-wrap{position:relative}
.eye{position:absolute; right:12px; top:14px; cursor:pointer}
button{width:100%; padding:13px; background:#f68b1e; color:#fff; border:none; border-radius:5px; font-weight:bold; margin-top:10px; cursor:pointer}
a{color:#f68b1e; text-decoration:none; font-size:14px}
.cat-bar{display:flex; gap:10px; overflow:auto; padding:10px; background:#fff}
.cat-bar span{padding:6px 12px; background:#eee; border-radius:20px; white-space:nowrap}
</style>
</head>
<body>
<div class="top">Ikokitufitii 👟 Eldoret - Jumia Style</div>

<div class="cat-bar">
  <span>All Shoes</span><span>Loafers</span><span>Sneakers</span><span>Heels</span><span>Official</span><span>Kids</span>
</div>

<div class="container">
  <h2>Create Account</h2>
  <p style="font-size:14px">Already have account? <a href="login.html">Login</a></p>
  
  <input id="name" placeholder="Full Name *">
  <input id="email" placeholder="Email Address *" type="email">
  
  <div class="pass-wrap">
    <input id="password" placeholder="Password *" type="password">
    <span class="eye" onclick="toggle('password')">👁️</span>
  </div>
  
  <div class="pass-wrap">
    <input id="confirm" placeholder="Confirm Password *" type="password">
    <span class="eye" onclick="toggle('confirm')">👁️</span>
  </div>

  <p><a href="#" onclick="forgot()">Forgot Password?</a></p>
  
  <button onclick="createAccount()">CREATE ACCOUNT</button>
  <p id="msg" style="font-size:13px"></p>
  
  <p style="font-size:12px; color:#666; margin-top:15px">By creating account you agree to our Terms. Delivery: CBD 200, Langas 350, Elgon View 400</p>
</div>

<script src="https://cdn.jsdelivr.net/npm/@emailjs/browser@3/dist/email.min.js"></script>
<script>
emailjs.init("YOUR_EMAILJS_PUBLIC_KEY"); // I'll give you key next

const API = "https://ed-parts-shop.onrender.com";
function toggle(id){
  const el=document.getElementById(id);
  el.type = el.type==='password' ? 'text' : 'password';
}

async function createAccount(){
  const name=document.getElementById('name').value.trim();
  const email=document.getElementById('email').value.trim();
  const pass=document.getElementById('password').value;
  const confirm=document.getElementById('confirm').value;
  
  if(!name || !email || !pass){ msg.innerText="Fill all *"; return; }
  if(pass!==confirm){ msg.innerText="Passwords don't match"; return; }

  msg.innerText="Creating...";
  const res = await fetch(API+'/api/register',{
    method:'POST', headers:{'Content-Type':'application/json'},
    body:JSON.stringify({name,email,password:pass})
  });
  const data=await res.json();
  if(data.error){ msg.innerText=data.error; }
  else { 
    msg.innerText="Success! Redirecting to login...";
    localStorage.setItem('userName', data.name);
    setTimeout(()=> location.href='login.html', 1000);
  }
}

async function forgot(){
  const email=document.getElementById('email').value.trim();
  if(!email){ msg.innerText="Enter email first to reset"; return; }
  msg.innerText="Sending reset code to email...";
  
  const res = await fetch(API+'/api/forgot-password',{
    method:'POST', headers:{'Content-Type':'application/json'},
    body:JSON.stringify({email})
  });
  const data=await res.json();
  
  // SEND REAL EMAIL with code
  const code = data.reset_link ? data.reset_link.split('token=')[1].slice(0,6).toUpperCase() : Math.floor(100000+Math.random()*900000);
  
  try{
    await emailjs.send("service_id","template_id",{
      to_email: email,
      reset_code: code,
      reset_link: data.reset_link
    });
    msg.innerText=`Code sent to ${email}. Code: ${code}`;
    localStorage.setItem('reset_code', code);
    localStorage.setItem('reset_email', email);
    setTimeout(()=> location.href=`reset.html?token=${data.reset_link?.split('token=')[1] || ''}`, 1500);
  }catch(e){
    // MVP fallback: show link
    msg.innerText = data.message + " Link: " + data.reset_link;
    alert("Reset link (MVP): " + data.reset_link);
  }
}
</script>
</body>
</html>
