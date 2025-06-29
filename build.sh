#!/bin/bash

# Set non-interactive mode
export DEBIAN_FRONTEND=noninteractive

# Install system dependencies
apt-get update && apt-get install -y \
  ffmpeg \
  imagemagick \
  ttf-dejavu \
  && rm -rf /var/lib/apt/lists/*

# Install Python packages
pip install --upgrade pip
pip install -r requirements.txt
