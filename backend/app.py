import os
import redis
from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app) # Enable CORS for all routes

# Connect to Redis
redis_host = os.environ.get('REDIS_HOST', 'localhost')
redis_port = int(os.environ.get('REDIS_PORT', 6379))
r = redis.Redis(host=redis_host, port=redis_port, db=0, decode_responses=True)

# --- Application State & Data ---

# In a real application, mode changes would be triggered by external events (e.g., sensors, gestures)
# For now, it's hardcoded but could be stored in Redis or another mechanism.
current_mode = "standby" # or "menu"

HABITS = [
    "Brush Teeth",
    "Floss",
    "Take Vitamins",
    "Meditate (5 min)",
    "Drink Water (1L)"
]

# Initialize habit completion status in Redis if not present
def initialize_habits():
    for habit in HABITS:
        if r.exists(habit) == 0:
            r.set(habit, "false") # Store as strings "true"/"false"

initialize_habits()

# --- API Endpoints ---

@app.route('/')
def hello_world():
    # Basic health check or info endpoint
    return jsonify({"message": "Magic Mirror Backend Running", "redis_connected": r.ping()})

@app.route('/mode')
def get_mode():
    # TODO: Implement logic to dynamically change the mode based on external triggers
    # For now, returning the hardcoded mode
    return jsonify({"mode": current_mode})

# Example endpoint to manually change mode (for testing)
@app.route('/mode/set/<new_mode>', methods=['POST'])
def set_mode(new_mode):
    global current_mode
    if new_mode in ["standby", "menu"]:
        current_mode = new_mode
        return jsonify({"message": f"Mode set to {current_mode}"}), 200
    else:
        return jsonify({"error": "Invalid mode"}), 400

@app.route('/habits')
def get_habits():
    habits_status = []
    for habit in HABITS:
        completed = r.get(habit) == "true"
        habits_status.append({"name": habit, "completed": completed})
    return jsonify(habits_status)

@app.route('/habits/<habit_name>/toggle', methods=['POST'])
def toggle_habit(habit_name):
    if habit_name not in HABITS:
        return jsonify({"error": "Habit not found"}), 404
    
    current_status = r.get(habit_name) == "true"
    new_status = not current_status
    r.set(habit_name, str(new_status).lower()) # Store as "true" or "false"
    
    return jsonify({"name": habit_name, "completed": new_status})


if __name__ == '__main__':
    # Debug mode is automatically enabled by FLASK_ENV=development in docker-compose
    app.run(host='0.0.0.0', port=5001) 