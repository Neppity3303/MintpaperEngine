#!/bin/bash
export DISPLAY=:0
export XDG_CURRENT_DESKTOP=Cinnamon
cd "/home/brandon/MintpaperEngine"
"./venv/bin/python3" "main.py" >> "/home/brandon/MintpaperEngine/startup_error.log" 2>&1
