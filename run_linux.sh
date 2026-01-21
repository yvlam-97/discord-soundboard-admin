#!/bin/bash

source bot-env/bin/activate
pip install -r requirements.txt

nohup python soundboard_web.py > soundboard_web.log 2>&1 &
nohup python main.py > main.log 2>&1 &

wait