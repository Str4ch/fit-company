import http.client
import json
from dotenv import load_dotenv
import os

load_dotenv()
host = os.getenv("HOST")
email = os.getenv("EMAIL")
password = os.getenv("PASSWORD")
port = os.getenv("PORT")

conn = http.client.HTTPConnection(host, port)

body = {
    "email": email,
    "password": password
}


conn.request("POST","/oauth/token", json.dumps(body), {"Content-Type": "application/json"})

response = conn.getresponse()

access_token=json.loads(response.read().decode())["access_token"]

conn.request("POST", "users/generateWods", None, headers={ 'Authorization': f'Bearer {access_token}' })

response = conn.getresponse()
print(response.status, response.reason)