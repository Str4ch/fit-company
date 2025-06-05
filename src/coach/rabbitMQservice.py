import json
import os
import pika
from .fitness_coach_service import create_wod
from .database import db_session
from .models_db import WodForUser
from datetime import datetime

class RabbitMQService:
    def __init__(self):
        self.connection = None
        self.channel = None
        self.queue_name = "createWodQueue"
        self.connect()

    def connect(self):
        """Establish connection to RabbitMQ server"""
        credentials = pika.PlainCredentials(
            username=os.getenv("RABBITMQ_DEFAULT_USER", "rabbit"),
            password=os.getenv("RABBITMQ_DEFAULT_PASS", "docker")
        )
        parameters = pika.ConnectionParameters(
            host=os.getenv("RABBITMQ_HOST", "rabbitmq"),
            port=5672,
            credentials=credentials,
            heartbeat=600,
            blocked_connection_timeout=300
        )
        self.connection = pika.BlockingConnection(parameters)
        self.channel = self.connection.channel()

        # Declare the main queue with message TTL of 10 minutes (600000 ms)
        # and max length of 100 messages
        arguments = {
            "x-message-ttl": 600000,  # 10 minutes
            "x-max-length": 100,
            "x-dead-letter-exchange": "dlx",  # Dead Letter Exchange
            "x-dead-letter-routing-key": f"{self.queue_name}-dead"
        }
        
        # Declare the Dead Letter Exchange and Queue
        self.channel.exchange_declare(exchange="dlx", exchange_type="direct")
        self.channel.queue_declare(queue=f"{self.queue_name}-dead", durable=True)
        self.channel.queue_bind(
            exchange="dlx",
            queue=f"{self.queue_name}-dead",
            routing_key=f"{self.queue_name}-dead"
        )

        # Declare the main queue
        self.channel.queue_declare(
            queue=self.queue_name,
            durable=True,
            arguments=arguments
        )

    def receive_message(self) -> bool:
        """Publish a message to the queue"""
        try:
            if not self.connection or self.connection.is_closed:
                self.connect()
            db = db_session()
            print("Waiting for messages in RabbitMQ...")
            def callback(ch, method, properties, body):
                bd = json.loads(body.decode())
                exercises = create_wod(bd["email"])
                for exercise_model in exercises.exercises:
                    print(f"Exercise: {exercise_model}")
                wd_response =[
                    exercise_model.model_dump_json()
                    for exercise_model in  exercises.exercises
                ]
                db.add(
                    WodForUser(
                        user_email=bd["email"],
                        wod_response=wd_response,
                        generated_at=datetime.now()
                    )
                )
                db.commit()

            self.channel.basic_consume(queue=self.queue_name,
                      auto_ack=True,
                      on_message_callback=callback)
            self.channel.start_consuming()

            return True
        except Exception as e:
            print(f"Error publishing message to RabbitMQ: {str(e)}")
            return False
        


    def close(self):
        """Close the connection"""
        if self.connection and not self.connection.is_closed:
            self.connection.close()

# Create a singleton instance
rabbitmq_service = RabbitMQService() 