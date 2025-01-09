#!/bin/bash

# Install system dependencies
apt-get update
apt-get install -y libasound2-dev portaudio19-dev python3-all-dev python-all-dev libportaudio2 libportaudiocpp0 ffmpeg

# Install Python dependencies
pip install --upgrade pip
pip install -r requirements.txt
