from flask import Flask, render_template
from flask_socketio import SocketIO
import random
import time
import threading

app = Flask(__name__, template_folder='.')
socketio = SocketIO(app, cors_allowed_origins="*")

# Function to simulate real-time microplastic detection
def generate_data():
    while True:
        data = [
            {"microplastic": "Polyethylene", "concentration": round(random.uniform(1, 10), 2)},
            {"microplastic": "Polypropylene", "concentration": round(random.uniform(1, 10), 2)},
            {"microplastic": "Polystyrene", "concentration": round(random.uniform(1, 10), 2)}
        ]
        socketio.emit('update_data', data)
        time.sleep(3)  # Send new data every 3 seconds

@app.route('/')
def home():
    return render_template('Web_Dashboard.html')  # Ensure this matches your HTML file name

if __name__ == '__main__':
    threading.Thread(target=generate_data, daemon=True).start()
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
