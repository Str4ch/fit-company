import datetime
import json
import os
from queue import Full
from typing import List, Tuple

import requests

from .models_dto import MuscleGroupImpact, WodExerciseSchema, WodResponseSchema
from .models_db import ExerciseModel, MuscleGroupModel, exercise_muscle_groups, WodForUser
from .database import db_session
import random
from time import time

def heavy_computation(duration_seconds: int = 3):
    """
    Perform CPU-intensive calculations to simulate heavy processing.
    Uses matrix operations which are CPU-intensive.
    """
    start_time = time()
    i = 0
    while (time() - start_time) < duration_seconds:
        j = 0
        while j < 1000000:
            j += 1
        i += 1

def calculate_intensity(difficulty: int) -> float:
    """
    Calculate the intensity of an exercise based on its difficulty level (1-5).
    Returns a value between 0.0 and 1.0.
    """
    # Convert difficulty (1-5) to intensity (0.0-1.0)
    return (difficulty - 1) / 4.0

def get_last_workout_exercises(user_email: str) -> List[int]:
    """
    Get the last workout exercises for a user from the monolith.
    """
    monolith_url = os.getenv("MONOLITH_URL")
    headers = {"X-API-Key": os.getenv("FIT_API_KEY")}
    history_response = requests.post(f"{monolith_url}/workouts/last", headers=headers, json={"email": user_email})
    history_response.raise_for_status()
    history_exercises = history_response.json()

    return [history_exercise["id"] for history_exercise in history_exercises]

def save_workout_exercises(user_email: str, exercise_ids: List[int]):
    """
    Save the workout exercises for a user to the monolith.
    """
    monolith_url = os.getenv("MONOLITH_URL")
    headers = {"X-API-Key": os.getenv("FIT_API_KEY")}
    requests.post(f"{monolith_url}/workouts/register", headers=headers, json={"email": user_email, "exercises": exercise_ids})


def request_wod(user_email: str) -> List[Tuple[ExerciseModel, List[Tuple[MuscleGroupModel, bool]]]]:
    """
    Request a workout of the day (WOD).
    Returns a list of tuples containing:
    - The exercise
    - A list of tuples containing:
      - The muscle group
      - Whether it's a primary muscle group
    
    Avoids repeating exercises from the user's last workout.
    """
    # Simulate heavy computation (AI model processing, complex calculations, etc.) for 1-5 seconds
    heavy_computation(random.randint(1, 5)) # DO NOT REMOVE THIS LINE
    
    db = db_session()
    
    try:

        last_exercise_ids = get_last_workout_exercises(user_email)

        available_exercises = db.query(ExerciseModel).filter(
            ~ExerciseModel.id.in_(last_exercise_ids)
        ).all()

        # If we don't have enough exercises (excluding last workout's), include all exercises
        if len(available_exercises) < 6:
            available_exercises = db.query(ExerciseModel).all()
        
        # Select 6 random exercises
        selected_exercises = random.sample(available_exercises, 6) if len(available_exercises) >= 6 else available_exercises
        
        # Store today's exercises in history
        save_workout_exercises(user_email, [exercise.id for exercise in selected_exercises])
        
        # For each exercise, get its muscle groups and whether they are primary
        result = []
        for exercise in selected_exercises:
            # Get the junction table information for this exercise
            stmt = db.query(
                MuscleGroupModel,
                exercise_muscle_groups.c.is_primary
            ).join(
                exercise_muscle_groups,
                MuscleGroupModel.id == exercise_muscle_groups.c.muscle_group_id
            ).filter(
                exercise_muscle_groups.c.exercise_id == exercise.id
            )
            
            muscle_groups = [(mg, is_primary) for mg, is_primary in stmt.all()]
            result.append((exercise, muscle_groups))
        return result
    finally:
        db.close()

def create_wod(user_email: str) -> List[Tuple[ExerciseModel, List[Tuple[MuscleGroupModel, bool]]]]:
    if not user_email:
        return Full
        
    try:
        # Fetch user last workout exercises from monolith
        # app.logger.debug(f"History exercises: {history_exercises}")
        exercises_with_muscles = request_wod(user_email)
        wod_exercises = []
        for exercise, muscle_groups in exercises_with_muscles:
            # Create muscle group impact objects
            muscle_impacts = [
                MuscleGroupImpact(
                    id=mg.id,
                    name=mg.name,
                    body_part=mg.body_part,
                    is_primary=is_primary,
                    # Higher intensity for primary muscle groups
                    intensity=calculate_intensity(exercise.difficulty) * (1.2 if is_primary else 0.8)
                )
                for mg, is_primary in muscle_groups
            ]
            
            # Create exercise object
            wod_exercise = WodExerciseSchema(
                id=exercise.id,
                name=exercise.name,
                description=exercise.description,
                difficulty=exercise.difficulty,
                muscle_groups=muscle_impacts,
                suggested_weight=random.uniform(5.0, 50.0),  # Random weight between 5 and 50 kg
                suggested_reps=random.randint(8, 15)  # Random reps between 8 and 15
            )
            wod_exercises.append(wod_exercise)
        
        response = WodResponseSchema(
            exercises=wod_exercises,
            generated_at=datetime.datetime.now(datetime.UTC).isoformat()
        )
        
        return response

        
    except requests.RequestException as e:
        return {"error": f"Failed to fetch user history: {str(e)}"}, 500
    
def recieve_wods(user_email: str) -> WodResponseSchema:
    """
    Receive WODs from RabbitMQ for a specific user.
    """
    if not user_email:
        return Full

    try:
        db = db_session()
        users_wods_today = db.query(WodForUser).filter_by(user_email=user_email, generated_at=datetime.datetime.now().date()).all()
        if not users_wods_today:
            return create_wod(user_email)
        exercises_today = [json.loads(wod) for wod in users_wods_today[0].wod_response]
        response = WodResponseSchema(
            exercises=exercises_today,
            generated_at=users_wods_today[0].generated_at
        )
        return response
    
    except Exception as e:
        print(f"Error receiving WODs: {str(e)}")
        return {"error": str(e)}, 500