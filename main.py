from flask import Flask, render_template, request, redirect, url_for
import requests
import json
from datetime import datetime

app = Flask(__name__)

# Base URL for Twitter API
BASE_URL = 'https://api.twitter.com/1.1/'

# Global variables to store Twitter API credentials and message details
api_key = None
api_secret = None
access_token = None
selected_dm = None

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        global api_key, api_secret
        api_key = request.form['api_key']
        api_secret = request.form['api_secret']
        authenticate(api_key, api_secret)
        return redirect(url_for('messages'))
    return render_template('index.html')

@app.route('/messages', methods=['GET', 'POST'])
def messages():
    if request.method == 'POST':
        global selected_dm
        selected_dm = request.form['dm_id']
        return redirect(url_for('open_message'))
    else:
        dms = pull_dms(access_token).get('events', [])
        # Format the date within each message
        for dm in dms:
            if 'created_timestamp' in dm:
                # Assuming the timestamp is in a format that datetime can parse directly
                dm['formatted_date'] = datetime.fromtimestamp(
                    int(dm['created_timestamp']) / 1000  # Convert milliseconds to seconds if needed
                ).strftime('%Y-%m-%d')
        return render_template('messages.html', dms=dms)

@app.route('/open_message', methods=['GET', 'POST'])
def open_message():
    global selected_dm
    dm_id = selected_dm
    dm_details = get_dm_details(dm_id)
    if request.method == 'POST':
        recipient_id = dm_details['message_create']['sender_id']
        message = request.form['comment']
        respond_to_dm(recipient_id, message)
    return render_template('open_message.html', dm_details=dm_details)

@app.route('/open_on_twitter', methods=['POST'])
def open_on_twitter():
    global selected_dm
    dm_id = selected_dm
    open_message(dm_id)
    return redirect(url_for('open_message'))

# Authenticate with Twitter API
def authenticate(api_key, api_secret):
    global access_token
    auth_response = requests.post(
        'https://api.twitter.com/oauth2/token',
        auth=(api_key, api_secret),
        headers={'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8'},
        data={'grant_type': 'client_credentials'}
    )
    if auth_response.status_code == 200:
        access_token = auth_response.json().get('access_token')
        print("Access Token successfully retrieved:", access_token)
    else:
        access_token = None  # Clear the access token if authentication fails
        print("Failed to authenticate:", auth_response.json())

# Pull all direct messages
def pull_dms(access_token):
    url = BASE_URL + 'direct_messages/events/list.json'
    headers = {'Authorization': f'Bearer {access_token}'}
    response = requests.get(url, headers=headers)
    print("DM Response:", response.json())  # Log the raw response
    if response.status_code == 200:
        return response.json()
    else:
        return {'events': []}  # Return an empty list if there's an error

# Get details of a specific direct message
def get_dm_details(dm_id):
    url = BASE_URL + 'direct_messages/events/show.json'
    headers = {'Authorization': f'Bearer {access_token}'}
    params = {'id': dm_id}
    response = requests.get(url, headers=headers, params=params)
    return response.json()

# Respond to direct message
def respond_to_dm(recipient_id, message):
    url = BASE_URL + 'direct_messages/events/new.json'
    headers = {'Authorization': f'Bearer {access_token}', 'Content-Type': 'application/json'}
    data = {
        "event": {
            "type": "message_create",
            "message_create": {
                "target": {"recipient_id": recipient_id},
                "message_data": {"text": message}
            }
        }
    }
    response = requests.post(url, headers=headers, data=json.dumps(data))
    return response.json()

if __name__ == '__main__':
    app.run(debug=True)
