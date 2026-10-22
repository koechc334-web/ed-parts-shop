from flask import Flask
app = Flask(__name__)

@app.route('/')
def home():
    try:
        with open('index.html', 'r') as f:
            return f.read()
    except:
        return "Ed Parts Shop is Live!"

if __name__ == '__main__':
    app.run()
