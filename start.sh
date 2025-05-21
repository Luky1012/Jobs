#!/bin/bash
# Gunicorn configuration for LinkedIn Job Application Automation Web App

# Set environment variables
export FLASK_APP=src.main
export FLASK_ENV=production
export PYTHONPATH=/home/ubuntu/linkedin_job_app_web

# Start Gunicorn server
exec gunicorn --bind 0.0.0.0:5000 --workers 2 --timeout 120 src.main:app
