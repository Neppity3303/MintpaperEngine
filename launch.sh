#!/bin/bash
export DISPLAY=:0
cd "/home/brandon/Documents/MintPaperEngine"
"./venv/bin/python3" "main.py" > "/home/brandon/Documents/MintPaperEngine/startup_error.log" 2>&1
