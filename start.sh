#!/bin/bash

# Debug information
echo "Script path (\$0): $0"
echo "Script directory: $(dirname "$0")"

# Change to the directory where the script is located
cd "$(dirname "$0")"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Virtual environment not found. Creating one..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

# Export Flask app variable
export FLASK_APP=main.py

# Check if --dev flag is passed
if [[ $1 == "--dev" ]]; then
    export FLASK_ENV=development
    echo "Starting in development mode..."
fi

# TODO: decide what persistence is required, and create redis .conf file

# run redis-server in the background
redis-server &
# Run Flask application
flask run 