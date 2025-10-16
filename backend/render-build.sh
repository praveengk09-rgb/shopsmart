#!/usr/bin/env bash
# Install Chrome and its driver for Selenium
apt-get update
apt-get install -y wget unzip chromium chromium-driver

# Build the frontend
cd ../frontend
npm install
npm run build

# Back to backend, install Python deps
cd ../backend
pip install -r requirements.txt
