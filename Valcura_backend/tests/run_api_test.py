import requests
import json
import time

url = 'http://127.0.0.1:8000/api/missed-call/webhook/'
payload = {
    'event': 'missed_call',
    'number': '+19876543210'
}
headers = {'Content-Type': 'application/json'}

try:
    # Give the server a moment to start up completely
    time.sleep(2)
    response = requests.post(url, data=json.dumps(payload), headers=headers)
    print("Status Code:", response.status_code)
    print("Response Content:", response.json())
except Exception as e:
    print("Error:", e)
