from flask import Flask, render_template, request, redirect, url_for, session
import pandas as pd
import requests
from io import StringIO
import sys
import os
import tempfile
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'lib')))

import read_price_csv
import shared
import update_dealer_prices
import update_dynamic_prices
import main

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Used for session management

# Static password for simplicity
ADMIN_PASSWORD = ''

def get_config():
    # Get the absolute path of the current script
    current_script_path = os.path.abspath(__file__)

    # Get the parent directory of the script (one level up)
    parent_directory = os.path.dirname(current_script_path)

    # Get the grandparent directory (one level up from the parent directory)
    grandparent_directory = os.path.dirname(parent_directory)

    config_filename = 'config.json'
    file_path = os.path.join(grandparent_directory, config_filename)
    print(file_path)
    with open(file_path, 'r') as file:
        config = json.load(file)
        return config
    

# Home page with login
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        config = get_config()

        password = request.form['password']
        if password == config['webapp-secret']:
            session['logged_in'] = True
            return redirect(url_for('upload_csv'))
        else:
            return 'Invalid password. Please try again.'

    return render_template('index.html')


# Upload CSV page
@app.route('/upload', methods=['GET', 'POST'])
def upload_csv():
    if not session.get('logged_in'):
        return redirect(url_for('index'))  # Redirect to login if not logged in

    if request.method == 'POST':
        config = get_config()

        csv_file = request.files['csv_file']
        
        if csv_file:
            update_dealer_prices = 'update_dealer_prices' in request.form
            update_distributor_prices = 'update_distributor_prices' in request.form

            # Print or log for debugging
            print(f"Update Dealer Prices: {update_dealer_prices}")
            print(f"Update Distributor Prices: {update_distributor_prices}")
            # Save the uploaded file temporarily
            with tempfile.NamedTemporaryFile(delete=False, mode='wb') as temp_file:
                temp_file.write(csv_file.read())
                temp_file_path = temp_file.name

            try:
                dealer_error_df, dealer_success_df, dealer_log, distributor_log = main.main(temp_file_path, update_dealer_prices, update_distributor_prices, config)

                return render_template('result.html', dealer_log=dealer_log, distributor_log=distributor_log)

            finally:
                # Clean up the temporary file after use
                if os.path.exists(temp_file_path):
                    os.remove(temp_file_path)

    return render_template('upload.html')


# Logout route
@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('index'))


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)