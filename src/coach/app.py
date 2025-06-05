from flask import Flask, request, jsonify
import os
import logging
import threading


from .fitness_coach_service import recieve_wods

from .fitness_service import get_exercises_by_muscle_group, get_all_exercises, get_exercise_by_id

from .database import init_db
from .fitness_data_init import init_fitness_data

# Configure Flask logging
logging.basicConfig(level=logging.DEBUG)
app = Flask(__name__)
app.logger.setLevel(logging.DEBUG)

# Force stdout to be unbuffered
import sys
sys.stdout.reconfigure(line_buffering=True)

# Validate required environment variables
if not os.getenv("FIT_API_KEY"):
    raise RuntimeError("FIT_API_KEY environment variable must be set")

def start_rabbitmq_consumer():
    from .rabbitMQservice import rabbitmq_service
    rabbitmq_service.receive_message()


threading.Thread(target=start_rabbitmq_consumer, daemon=True).start()

# Register blueprints
@app.route("/health")
def health():
    return {"status": "UP"}

@app.route("/exercises", methods=["GET"])
def get_exercises():
    try:
        muscle_group_id = request.args.get("muscle_group_id")
        if muscle_group_id:
            # Get exercises for a specific muscle group
            exercises = get_exercises_by_muscle_group(int(muscle_group_id))
        else:
            # Get all exercises
            exercises = get_all_exercises()
        return jsonify([ex.model_dump() for ex in exercises]), 200
    except Exception as e:
        return jsonify({"error": "Error retrieving exercises", "details": str(e)}), 500

@app.route("/exercises/<int:exercise_id>", methods=["GET"])
def get_exercise(exercise_id):
    try:
        exercise = get_exercise_by_id(exercise_id)
        if not exercise:
            return jsonify({"error": "Exercise not found"}), 404
        return jsonify(exercise.model_dump()), 200
    except Exception as e:
        return jsonify({"error": "Error retrieving exercise", "details": str(e)}), 500

@app.route("/getWod", methods=["POST"])
def get_wods():
    user_email = request.json.get("user_email")
    if not user_email:
        return jsonify({"error": "user_email is required"}), 400

    try:
        wod_response = recieve_wods(user_email)
        if not wod_response:
            return jsonify({"error": "No WODs available for this user"}), 404
        
        return jsonify(wod_response.model_dump()), 200

    except Exception as e:
        return jsonify({"error": "Error retrieving WOD", "details": str(e)}), 500


def run_app():
    """Entry point for the application script"""
    # Initialize the database before starting the app
    init_db()

    init_fitness_data()
    app.run(host="0.0.0.0", port=5000, debug=True)

if __name__ == "__main__":
    run_app()

