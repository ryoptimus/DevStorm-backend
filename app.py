# app.py
import os
import redis
from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_bcrypt import Bcrypt
from flask_mail import Mail
from datetime import timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Create bcrypt object
bcrypt = Bcrypt()

# Initialize JWTManager
jwt = JWTManager()

# Create mail object
mail = Mail()

def create_app():
    app = Flask(__name__)

    # Configure CORS
    CORS(app, resources={
        r'/user': {'origins': os.getenv("FRONTEND")},
        r'/user/*': {'origins': os.getenv("FRONTEND")},
        r'/register': {'origins': os.getenv("FRONTEND")},
        r'/api/prompt': {'origins': os.getenv("FRONTEND")},
        r'/login': {'origins': os.getenv("FRONTEND")},
        r'/logout': {'origins': os.getenv("FRONTEND")},
        r'/token/*': {'origins': os.getenv("FRONTEND")},
        r'/project': {'origins': os.getenv("FRONTEND")},
        r'/project/*': {'origins': os.getenv("FRONTEND")},
        r'/task': {'origins': os.getenv("FRONTEND")},
        r'/task/*': {'origins': os.getenv("FRONTEND")},
        r'/confirm/*': {'origins': os.getenv("FRONTEND")},
        r'/get_csrf_tokens': {'origins': os.getenv("FRONTEND")}
    }, supports_credentials=True)
    
    app.config['FRONTEND_URL'] = os.getenv("FRONTEND")
    # Add itsdangerous secret key and password salt from .env variables
    app.config['ITSDANGEROUS_SECRET_KEY'] = os.getenv("ITSDANGEROUS_SECRET_KEY")
    app.config['ITSDANGEROUS_PASSWORD_SALT'] = os.getenv("ITSDANGEROUS_PASSWORD_SALT")
    
    # Set up flask mail
    app.config['MAIL_SERVER'] = 'smtp.gmail.com'
    app.config['MAIL_PORT'] = 587
    app.config['MAIL_USE_TLS'] = True
    app.config['MAIL_USE_SSL'] = False
    app.config['MAIL_USERNAME'] = os.getenv("MAIL_USERNAME")
    app.config['MAIL_PASSWORD'] = os.getenv("MAIL_PASSWORD")
    app.config['MAIL_DEFAULT_SENDER'] = os.getenv("MAIL_USERNAME")
    
    # Setup the Flask-JWT-Extended extension
    app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY")
    # Enable blocklisting; specify which tokens to check
    # app.config['JWT_BLACKLIST_ENABLED'] = True
    # app.config['JWT_BLACKLIST_TOKEN_CHECKS'] = ['access', 'refresh']
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
    
    # Create Redis client instance
    #   decode_response=True -> tells Redis to return strings rather than bytes
    app.blocklist = redis.StrictRedis(
        host="localhost", port=6379, db=0, decode_responses=True
    )
    
    # Initialize JWT with the app
    jwt.init_app(app)
    # Initialize bcrypt with the app
    bcrypt.init_app(app)
    # Initialize Flask-Mail with the app
    mail.init_app(app)
    return app, jwt, bcrypt