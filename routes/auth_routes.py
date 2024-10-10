# auth_routes.py

import mysql.connector
from flask import Blueprint, jsonify, request, current_app, url_for, render_template
from flask_jwt_extended import (
    create_access_token, create_refresh_token,
    jwt_required, get_jwt, get_jwt_identity, set_access_cookies, set_refresh_cookies,
    unset_jwt_cookies, verify_jwt_in_request
)
from mysql.connector import IntegrityError
from datetime import datetime, timedelta
from app import bcrypt, jwt
from db import get_db_connection
from helpers import (
  hash_password, verify_password, generate_confirmation_token, confirm_token, send_email
)

auth_bp = Blueprint('auth_bp', __name__)

def add_to_blocklist(jti):
  current_app.blocklist.set(jti, "", ex=timedelta(minutes=30))
  
def print_blocklist():
  print("Printing blocklist")
  keys = current_app.blocklist.keys('*')
  if not keys:
    print("Blocklist is empty")
    return
  
  for key in keys:
    # Get TTL (time-to-live) for each key
    ttl = current_app.blocklist.ttl(key)
    print(f"Blocked jti: {key}, expires in {ttl} seconds")

# REGISTER
@auth_bp.route('/register', methods=['POST'])
def register_user():
  data = request.get_json()
  email = data['email']
  username = data['username']
  password = data['password']
  hashed_password = hash_password(password, bcrypt)
  connection = get_db_connection()
  if connection:
    try:
      cursor = connection.cursor()
      date_joined = datetime.now()
      query = "INSERT INTO users (email, username, password, membership, date_joined) VALUES (%s, %s, %s, %s, %s)"
      cursor.execute(query, (email, username, hashed_password, "STANDARD", date_joined))
      # Commit changes
      connection.commit()
      
      confirmation_token = generate_confirmation_token(email)
      confirmation_url = url_for('auth_routs.confirm_email', token=confirmation_token, _external=True)
      
      # Generate access token for new user
      access_token = create_access_token(identity=username, fresh=True)
      refresh_token = create_refresh_token(identity=username)
      response = jsonify({"message": "Registration successful, you are now logged in"})
      set_access_cookies(response, access_token)
      set_refresh_cookies(response, refresh_token)
      # 201 Created: User added/created successfully
      return response, 201
    except IntegrityError as e:
      # 400 Bad Request: Username already exists
      return jsonify({"error": "Username already exists."}), 400
    finally:
      # Close resources
      cursor.close()
      connection.close()
  # 500 Internal Server Error: Generic server-side failures
  return jsonify({"error": "Failed to connect to database"}), 500

@auth_bp.route('/confirm/<token>', methods=['GET'])
@jwt_required
def confirm_email(token):
  try:
    email = confirm_token(token)
  except:
    # 400 Bad Request
    return jsonify({"error": "The confirmation link is invalid or has expired"}), 400
  username = get_jwt_identity()
  connection = get_db_connection()
  if connection:
    try:
      cursor = connection.cursor()
      query_a = "SELECT * FROM users WHERE username = %s AND email = %s"
      cursor.execute(query_a, (username, email))
      user = cursor.fetchone()
      if not user:
        # 404 Not Found: User not found
        return jsonify({"error": "User not found"}), 404
      user_confirmed = user[4]
      if user_confirmed:
        return jsonify({"message": "Account already confirmed. Please login"}), 200
      else:
        query_b = "UPDATE users SET confirmed = 1 WHERE username = %s AND email = %s"
        cursor.execute(query_b, (username, email))
        query_c = "UPDATE users SET confirmed_on = %s WHERE username = %s AND email = %s"
        cursor.execute(query_c, (datetime.now(), username, email))
        connection.commit()
        return jsonify({"message": "You have successfully confirmed your account"}), 200
    except mysql.connector.Error as e:
      connection.rollback()
      # 500 Internal Server Error
      return jsonify({"error": f"Database error: {e}"}), 500
    finally:
         # Close resources
        cursor.close()
        connection.close()
  # 500 Internal Server Error: Generic server-side failures
  return jsonify({"error": "Failed to connect to database"}), 500
  

# LOGIN
# TODO: add try-except-finally
@auth_bp.route('/login', methods=['POST'])
def login():
  data = request.get_json()
  username = data['username']
  password = data['password']
    
  connection = get_db_connection()
  if connection:
    cursor = connection.cursor()
    # Structure query, retrieve user
    query = "SELECT * FROM users WHERE username = %s"
    cursor.execute(query, (username,))
    user = cursor.fetchone()
    # Close resources
    cursor.close()
    connection.close()
    
    # Check if user is found
    if user:
      # Retrieve stored password hash from user 
      stored_hash = user[3]
      # Check that passwords match
      if verify_password(password, stored_hash, bcrypt):
        # Create access and refresh tokens
        access_token = create_access_token(identity=username, fresh=True)
        refresh_token = create_refresh_token(identity=username)
        response = jsonify({"message": "Login verified", "access_token": access_token})
        # Store tokens in cookies
        set_access_cookies(response, access_token)
        set_refresh_cookies(response, refresh_token)
        # print(f"Login data:\n\tuser: {username}\n\taccess_token: {access_token}\n\trefresh_token: {refresh_token}")
        # 200 OK: For a successful request
        return response, 200
      else:
        # 401 Unauthorized: Request lacks valid authentication credentials
        return jsonify({"error": "Invalid credentials"}), 401
    else:
      # 401 Not Found: User not found
      return jsonify({"error": "User not found"}), 404
  # 500 Internal Server Error: Generic server-side failures
  return jsonify({"error": "Failed to connect to database"}), 500

@jwt.token_in_blocklist_loader
def token_in_blocklist(jwt_header, jwt_payload: dict):
  # print_blocklist()
  # Get token's unique identifier (jti)
  jti = jwt_payload['jti']
  token_in_redis = current_app.blocklist.get(jti)
  return token_in_redis is not None

@auth_bp.route('/token/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
  # Check for valid refresh token
  identity = get_jwt_identity()
  # Create new access token
  new_access_token = create_access_token(identity=identity, fresh=True)
  response = jsonify({"message": "Access token refreshed", "new_access token": new_access_token})
  # Store token in cookie
  set_access_cookies(response, new_access_token)
  # 200 OK: For a successful request that returns data
  return response, 200

# LOGOUT
@auth_bp.route('/logout', methods=['POST'])
def logout():
  response = jsonify({"message": "Logout successful"})
  try:
    # Try to verify the access token without requiring it
    verify_jwt_in_request(optional=True)
    access_token = get_jwt()
    if access_token:
      jti_access = access_token["jti"]
      add_to_blocklist(jti_access)
  except Exception:
    # Token might be expired, so skip blocklisting access token
    pass  

  try:
    # Try to verify the refresh token manually if present
    verify_jwt_in_request(optional=True, refresh=True)
    refresh_token = get_jwt(refresh=True)
    if refresh_token:
      jti_refresh = refresh_token["jti"]
      add_to_blocklist(jti_refresh)
  except Exception:
    # Token might be expired, so skip blocklisting refresh token
    pass  
  
  # Unset JWT cookies
  unset_jwt_cookies(response)
  
  # 200 OK: For a successful request that returns data
  return response, 200

@auth_bp.route('/get_csrf_tokens', methods=['GET'])
def get_csrf_tokens():
    # Retrieve the access token and refresh token from the cookies
    csrf_access_token = request.cookies.get('csrf_access_token')
    csrf_refresh_token = request.cookies.get('csrf_refresh_token')
    
    if not csrf_access_token or not csrf_refresh_token:
      # 400 Bad Request: Missing CSRF tokens
      return jsonify({"message": "Missing CSRF tokens"}), 400
    
    # 200 OK: For a successful request that returns data
    return jsonify({
        "csrf_access_token": csrf_access_token,
        "csrf_refresh_token": csrf_refresh_token
    }), 200