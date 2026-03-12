import os
import json
import requests

# Constants
URL = 'https://www.jumbo.cl/tomate-cocktail-frutas-y-verduras-jumbo-variedades/p'
STATE_FILE = 'state.json'

# Load previous state
if os.path.exists(STATE_FILE):
    with open(STATE_FILE, 'r') as f:
        state = json.load(f)
else:
    state = {}

# Fetch the page
response = requests.get(URL)
if response.status_code == 200:
    # Extract price from the page
    # This will depend on the structure of the webpage, adjust the selector accordingly.
    price = ...  # Add your logic to extract the price here

    # Update state
    state['price'] = price

    # Check if the price has changed
    if state.get('previous_price') != price:
        state['previous_price'] = price
        # Log the price change to GitHub issues
        issue_number = os.getenv('ISSUE_NUMBER')
        github_token = os.getenv('GITHUB_TOKEN')
        issue_url = f'https://api.github.com/repos/Mapaznavarro/mi-primer-Agente/issues/{{issue_number}}'
        headers = {'Authorization': f'token {{github_token}}'}
        data = {'body': f'The price of tomatoes has changed to {price} CLP.'}
        requests.post(issue_url, headers=headers, json=data)

    # Save the state
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f)
else:
    print('Failed to fetch the page.')