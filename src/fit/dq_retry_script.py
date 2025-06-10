#!/usr/bin/env python
import pika, sys, os, json
import http.client

from dotenv import load_dotenv
load_dotenv()
email = os.getenv("EMAIL")
password = os.getenv("PASSWORD")
host = os.getenv("HOST")
port = os.getenv("PORT")

conn = http.client.HTTPConnection(host, port)

body = {
    "email": email,
    "password": password
}

conn.request("POST","/oauth/token", json.dumps(body), {"Content-Type": "application/json"})

response = conn.getresponse()

access_token=json.loads(response.read().decode())["access_token"]

response.close()
conn.close()

def main():
    credentials = pika.PlainCredentials(
            username=os.getenv("RABBITMQ_DEFAULT_USER", "rabbit"),
            password=os.getenv("RABBITMQ_DEFAULT_PASS", "docker")
        )

    parameters = pika.ConnectionParameters(
            host=os.getenv("RABBITMQ_HOST", "localhost"),
            port=12104,
            credentials=credentials,
            heartbeat=600,
            blocked_connection_timeout=300
        )

    connection = pika.BlockingConnection(parameters)
    channel = connection.channel()

    queue_name = os.getenv("RABBITMQ_QUEUE_NAME", "createWodQueue-dead")

    channel.queue_declare(queue=queue_name, durable=True)

    def callback(ch, method, properties, body):
        bd = json.loads(body.decode())
        conn = http.client.HTTPConnection(host, port)
        conn.request("POST", "users/generateWods", body=json.dumps({"user_email": bd["email"]}), headers={ 'Authorization': f'Bearer {access_token}' })
        response = conn.getresponse()
        response.close()
        conn.close()

    channel.basic_consume(queue=queue_name, on_message_callback=callback, auto_ack=True)

    print(' [*] Waiting for messages. To exit press CTRL+C')
    channel.start_consuming()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('Interrupted')
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)
