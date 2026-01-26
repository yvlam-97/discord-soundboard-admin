#!/bin/bash

# Change to script directory
cd "$(dirname "$0")"

# Activate virtual environment
source bot-env/bin/activate

# Install/update dependencies
pip install -r requirements.txt

# Run the bot (web server is integrated)
python main.py