# app.py
import os
import redis
from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_bcrypt import Bcrypt
from datetime import timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Create bcrypt object
bcrypt = Bcrypt()

# Initialize JWTManager
jwt = JWTManager()

def create_app():
    app = Flask(__name__)

    # Configure CORS
    CORS(app, resources={
        r'/user': {'origins': [os.getenv("FRONTEND"), "http://127.0.0.1:3000"]},
        r'/user/*': {'origins': [os.getenv("FRONTEND"), "http://127.0.0.1:3000"]},
        r'/register': {'origins': [os.getenv("FRONTEND"), "http://127.0.0.1:3000"]},
        r'/api/prompt': {'origins': [os.getenv("FRONTEND"), "http://127.0.0.1:3000"]},
        r'/login': {'origins': [os.getenv("FRONTEND"), "http://127.0.0.1:3000"]},
        r'/logout': {'origins': [os.getenv("FRONTEND"), "http://127.0.0.1:3000"]},
        r'/token/refresh': {'origins': [os.getenv("FRONTEND"), "http://127.0.0.1:3000"]},
        r'/project': {'origins': [os.getenv("FRONTEND"), "http://127.0.0.1:3000"]},
        r'/project/*': {'origins': [os.getenv("FRONTEND"), "http://127.0.0.1:3000"]},
        r'/task': {'origins': [os.getenv("FRONTEND"), "http://127.0.0.1:3000"]},
        r'/task/*': {'origins': [os.getenv("FRONTEND"), "http://127.0.0.1:3000"]},
        r'/get_csrf_tokens': {'origins': os.getenv("FRONTEND")}
    }, supports_credentials=True)
    
    # Setup the Flask-JWT-Extended extension
    app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY")
    # Enable blocklisting; specify which tokens to check
    app.config['JWT_BLACKLIST_ENABLED'] = True
    app.config['JWT_BLACKLIST_TOKEN_CHECKS'] = ['access', 'refresh']
    # Set JWT access token expiry
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(minutes=30)
    # Set JWT refresh token expiry
    app.config["JWT_REFRESH_TOKEN_EXPIRES"] = timedelta(days=1)
    app.config['JWT_TOKEN_LOCATION'] = ['cookies']
    # Set to True if using HTTPS
    app.config['JWT_COOKIE_SECURE'] = False
    # Allow cross-site sharing between backend and frontend.
    # May need later for production use.
    # app.config['JWT_COOKIE_SAMESITE'] = 'None'
    # app.config["JWT_CSRF_IN_COOKIES"] = False
    # Enables CSRF (Cross-Site Request Forgery) protection for cookies
    # that store JWTs
    app.config['JWT_COOKIE_CSRF_PROTECT'] = True 
    # Cookie path to ensure cookie will be included in requests to the 
    # root URL and all branching paths
    app.config['JWT_ACCESS_COOKIE_PATH'] = '/'
    # Explicitly set separate path for refresh tokens
    app.config['JWT_REFRESH_COOKIE_PATH'] = '/' 
    
    app.blocklist = redis.StrictRedis(
        host="localhost", port=6379, db=0, decode_responses=True
    )
    
    #Initialize JWT with the app
    jwt.init_app(app)
    # Create bcrypt object
    bcrypt.init_app(app)
    return app, jwt, bcrypt