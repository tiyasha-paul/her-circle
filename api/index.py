import os
import sys

# Add the backend directory to the sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "backend"))

from app import app as application

# This is required for Vercel to find the Flask app
app = application
