#!/bin/bash

source bot-env/bin/activate

nohup python soundboard_web.py > soundboard_web.log 2>&1 &
nohup python main.py > main.log 2>&1 &

wait