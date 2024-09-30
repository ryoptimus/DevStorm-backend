import os
import json
from flask import Flask, request, jsonify
from flask_cors import CORS
import mysql.connector
from mysql.connector import IntegrityError
from dotenv import load_dotenv
from groq import Groq
from flask_jwt_extended import (
    JWTManager, create_access_token, create_refresh_token,
    jwt_required, get_jwt, get_jwt_identity, set_access_cookies, set_refresh_cookies,
    unset_jwt_cookies, verify_jwt_in_request
)
from flask_bcrypt import Bcrypt
from datetime import datetime, timedelta, timezone
from helpers import engineer_prompt, hash_password, verify_password, ProjectIdea

load_dotenv()

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
jwt = JWTManager(app)

# Create bcrypt object
bcrypt = Bcrypt(app)

# Create blocklist
blocklist = set()

@app.route("/")
def hello_world():
    return "Hello world!"

# Connect to database
def get_db_connection():
  try:
    connection = mysql.connector.connect(
      user=os.getenv("ADMIN_USER"), 
      password=os.getenv("ADMIN_PASSWORD"), 
      host=os.getenv("ENDPOINT"), 
      port=3306, 
      database=os.getenv("DB_NAME")
    )
    return connection
  except mysql.connector.Error as e:
    print(f"error: {e}")
    return None

# Generate table to store user information
def create_users_table():
  connection = get_db_connection()
  if connection:
    cursor = connection.cursor()
    try:
      # Drop previous table of same name if one exists
      # cursor.execute("DROP TABLE IF EXISTS users;")
      # print("Finished dropping 'users' table (if existed).")
      # Create table
      #   username:   50 char length. Standard for short-text fields
      #   email:      Max length 320
      #   membership: Two possible values - STANDARD or PREMIUM.
      #               MAX length value - STANDARD. 8 chars
      cursor.execute("""
          CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY, 
                email VARCHAR(320) UNIQUE,
                username VARCHAR(50) UNIQUE, 
                password VARCHAR(60),
                membership VARCHAR(8),
                projects INT DEFAULT 0,
                projects_completed INT DEFAULT 0,
                date_joined DATETIME
            );
        """)
      
      # Commit changes
      connection.commit()
    except mysql.connector.Error as e:
      print(f"Error creating 'users' table: {e}")
    finally:
      # Close resources
      cursor.close()
      connection.close()
  else:
    print("Failed to connect to database. Could not create 'users' table.")
    
def create_projects_table():
  connection = get_db_connection()
  if connection:
    cursor = connection.cursor()
    try:
      # Drop previous table of same name if one exists
      cursor.execute("DROP TABLE IF EXISTS projects;")
      print("Finished dropping 'projects' table (if existed).")
      # Create table
      #   summary:  255 char length. Standard for short-text fields
      #   steps:    JSON
      #   status:   Two possible values - COMPLETE or IN_PROGRESS.
      #             MAX length value - IN_PROGRESS. 11 chars
      cursor.execute("""
          CREATE TABLE IF NOT EXISTS projects (
                id INT AUTO_INCREMENT PRIMARY KEY, 
                username VARCHAR(50) UNIQUE, 
                title VARCHAR(60),
                summary VARCHAR(255),
                steps JSON,
                status VARCHAR(11)
            );
        """)
      print("Created table 'projects.'")
      
      # Commit changes
      connection.commit()
    except mysql.connector.Error as e:
      print(f"Error creating 'projects' table: {e}")
    finally:
      # Close resources
      cursor.close()
      connection.close()
  else:
    print("Failed to connect to database. Could not create 'projects' table.")

@app.route('/user/<username>', methods=['GET'])
def get_user(username):
  connection = get_db_connection()
  if connection:
    cursor = connection.cursor()
    query = "SELECT * FROM users WHERE username = %s"
    cursor.execute(query, (username,))
    # Check that cursor did not return none
    user = cursor.fetchone()
    # Close resources
    cursor.close()
    connection.close()
    if user:
      user_data = {
        "id": user[0], 
        "email": user[1], 
        "username": user[2],
        "password": user[3],
        "membership": user[4],
        "projects": user[5],
        "projects_completed": user[6],
        "date_joined": user[7]
      }
      # 200 OK: For a successful request that returns data
      return jsonify(user_data), 200
    else:
      # 404 Not Found: User not found
      return jsonify({"error": "User not found"}), 404
  # 500 Internal Server Error: Generic server-side failures
  return jsonify({"error": "Failed to connect to database"}), 500

# GET ALL
@app.route('/user', methods=['GET'])
def get_all_users():
  connection = get_db_connection()
  if connection:
    cursor = connection.cursor()
    query = "SELECT * FROM users"
    try:
      cursor.execute(query)
      users = cursor.fetchall()
      if users:
        users_list = [
          {
            "id": user[0], 
            "email": user[1],
            "username": user[2], 
            "password": user[3],
            "membership": user[4],
            "projects": user[5],
            "projects_completed": user[6],
            "date_joined": user[7]
          } 
          for user in users
        ]
        # 200 OK: For a successful request that returns data
        return jsonify(users_list), 200
      else:
        # 404 Not Found: Users not found
        return jsonify({"error": "No users found"}), 404
    except mysql.connector.Error as e:
      # 500 Internal Server Error: Generic server-side failures
      return jsonify({"error": str(e)}), 500
    finally:
      # Close resources
      cursor.close()
      connection.close()
  # 500 Internal Server Error: Generic server-side failures
  return jsonify({"error": "Failed to connect to database"}), 500

# REGISTER
@app.route('/register', methods=['POST'])
def register_user():
  data = request.get_json()
  email = data['email']
  username = data['username']
  password = data['password']
  membership = data['membership']
  hashed_password = hash_password(password, bcrypt)
  connection = get_db_connection()
  if connection:
    cursor = connection.cursor()
    date_joined = datetime.now()
    query = "INSERT INTO users (email, username, password, membership, date_joined) VALUES (%s, %s, %s, %s, %s)"
    try:
      cursor.execute(query, (email, username, hashed_password, membership, date_joined))
      # Commit changes
      connection.commit()
      # Generate access token for new user
      access_token = create_access_token(identity=username)
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

# LOGIN
@app.route('/login', methods=['POST'])
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
        print(f"Login data:\n\tuser: {username}\n\taccess_token: {access_token}\n\trefresh_token: {refresh_token}")
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
def token_in_blocklist(jwt_header, jwt_data):
  # Get token's unique identifier (jti)
  jti = jwt_data['jti']
  # print(f"blocklist: {list(blocklist)}")
  return jti in blocklist

@app.route('/token/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
  # Check for valid refresh token
  identity = get_jwt_identity()
  # Get token's unique identifier (jti)
  jti = get_jwt()['jti']
  # Add token's jti to blocklist
  blocklist.add(jti)
  # Create new access token
  new_access_token = create_access_token(identity=identity, fresh=True)
  response = jsonify({"message": "Access token refreshed"})
  # Store token in cookie
  set_access_cookies(response, new_access_token)
  # 200 OK: For a successful request that returns data
  return response, 200

# Using an `after_request` callback, we refresh any token that is within 15
# minutes of expiring. Change the timedeltas to match the needs of your application.
# @app.after_request
# def refresh_expiring_jwts(response):
    # try:
        # exp_timestamp = get_jwt()["exp"]
        # now = datetime.now(timezone.utc)
        # target_timestamp = datetime.timestamp(now + timedelta(minutes=15))
        # if target_timestamp > exp_timestamp:
            # access_token = create_access_token(identity=get_jwt_identity())
            # set_access_cookies(response, access_token)
        #200 OK
        # return response
    # except (RuntimeError, KeyError):
        # Case where there is not a valid JWT. Just return the original response
        # and 401 UNAUTHORIZED
        # return response

@app.route('/logout', methods=['POST'])
def logout():
  response = jsonify({"message": "Logout successful"})
  
  try:
    # Try to verify the access token without requiring it
    verify_jwt_in_request(optional=True)
    access_token = get_jwt()
    if access_token:
      jti_access = access_token["jti"]
      blocklist.add(jti_access)
  except Exception:
    # Token might be expired, so skip blocklisting access token
    pass  

  try:
    # Try to verify the refresh token manually if present
    verify_jwt_in_request(optional=True, refresh=True)
    refresh_token = get_jwt(refresh=True)
    if refresh_token:
      jti_refresh = refresh_token["jti"]
      blocklist.add(jti_refresh)
  except Exception:
    # Token might be expired, so skip blocklisting refresh token
    pass  
  
  # Unset JWT cookies
  unset_jwt_cookies(response)
  
  # 200 OK: For a successful request that returns data
  return response, 200

# UPDATE
# Updates password of a given user
@app.route('/user/<username>/update', methods=['PUT'])
@jwt_required()
def update_record(username):
  data = request.get_json()
  current_password = data['current_password']
  new_password = data['new_password']
  connection = get_db_connection()
  if connection:
    try:
      cursor = connection.cursor()
      # First, retrieve user by username (unique)
      query_a = "SELECT * FROM users WHERE username = %s"
      cursor.execute(query_a, (username,))
      user = cursor.fetchone()
      # Check if user is found
      if user:
        # Retrieve stored password hash for user
        stored_hash = user[2]
        # Check that current password matches stored password
        if verify_password(current_password, stored_hash, bcrypt):
          # Hash new password
          hashed_new_password = hash_password(new_password, bcrypt)
          # Set new (hashed) password
          query_b = "UPDATE users SET password = %s WHERE username = %s"
          cursor.execute(query_b, (hashed_new_password, username,))
          connection.commit()
          # 200 OK: For a successful request
          return jsonify({"message": "Password updated successfully"}), 200
        else:
          # 401 Unauthorized: Current password is incorrect
          return jsonify({"error": "Invalid current password"}), 401
      else:
        # 404 Not Found: User not found
        return jsonify({"error": "User not found"}), 404
    except mysql.connector.Error as e:
      # 500 Internal Server Error
      return jsonify({"error": f"Database error: {e}"}), 500
    finally:
      # Close resources
      cursor.close()
      connection.close()
  # 500 Internal Server Error: Generic server-side failures
  return jsonify({"error": "Failed to connect to database"}), 500

# DELETE
@app.route('/user/<username>/delete', methods=['DELETE'])
def delete_record(username):
  connection = get_db_connection()
  if connection:
    try:
      cursor = connection.cursor()
      query = "DELETE FROM users WHERE username = %s"
      cursor.execute(query, (username,))
      # Commit changes
      connection.commit()
      # 200 OK: For a successful request
      return jsonify({"message": "User deleted successfully."}), 200
    except mysql.connector.Error as e:
      # 500 Internal Server Error
      return jsonify({"error": f"Database error: {e}"}), 500
    finally:
      # Close resources
      cursor.close()
      connection.close()
  # 500 Internal Server Error: Generic server-side failures
  return jsonify({"error": "Failed to connect to database"}), 500

@app.route('/get_csrf_tokens', methods=['GET'])
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

# PROMPT
@app.route('/api/prompt', methods=['POST'])
# Ensure route /prompt can only be accessed by users with valid JWT
@jwt_required()
def prompt_ai():
  # Retrieve user identity from the JWT
  current_user = get_jwt_identity()
  # print(f"User '{current_user}' is authenticated.")
  data = request.get_json()
  roles = data['role']
  technologies = data['technology']
  industries = data['industries']
  prompt = engineer_prompt(roles, technologies, industries)
  print(f"Prompt: {prompt}")
  if not data:
    # 400 Bad Request: No inputs provided
    return jsonify({"error": "No inputs provided"}), 400
  try:
    # Initialize Groq instance
    client = Groq(api_key=os.getenv("GROQ_KEY"),)
    response = client.chat.completions.create(
      messages=[
        # Set the behavior of the assistant and provide instructions
        # for how it should behave while handling the prompt
        {
          "role": "system",
          # Pass the JSON schema to the model
          "content": (
            "You are a project assistant that outputs project ideas in JSON.\n"
            "The JSON object must use the schema: "
            f"{json.dumps(ProjectIdea.model_json_schema(), indent=2)}"
          ),
        },
        # Set user message
        {
          "role": "user",
          "content": prompt,
        },
      ],
      # Specify language model
      model="llama3-8b-8192",
      # Set temperature to 0 to encourage more deterministic output and reduced
      # randomness.
      temperature=0,
      # Streaming is not supported in JSON mode
      stream=False,
      # Enable JSON mode by setting the response format
      response_format={"type": "json_object"},
    )
    generated_text = response.choices[0].message.content
    print(f"Generated text: {generated_text}")
    # 200 OK: For a successful request that returns data
    return jsonify({"response": generated_text}), 200
  except Exception as e:
    # 500 Internal Server Error: Generic server-side failures
    return jsonify({"error": "Failed to call AI"}), 500
  
@app.route('/project/<username>', methods=['GET'])
def get_user_projects(username):
  connection = get_db_connection()
  if connection:
    cursor = connection.cursor()
    # Structure query, retrieve user
    query = "SELECT * FROM projects WHERE username = %s"
    cursor.execute(query, (username,))
    projects = cursor.fetchall()
    if projects:
      projects_list = [
          {
            "id": project[0], 
            "username": project[1], 
            "title": project[2],
            "summary": project[3],
            # Convert JSON string to list format
            "steps": json.loads(project[4]),
            "status": project[5]
          } 
          for project in projects
        ]
      # 200 OK: For a successful request that returns data
      return jsonify(projects_list), 200
    else:
      # 404 Not Found: Projects not found
      return jsonify({"error": f"No projects found for user 'username'"}), 404

# GET ALL PROJECTS
@app.route('/project', methods=['GET'])
def get_all_projects():
  connection = get_db_connection()
  if connection:
    cursor = connection.cursor()
    query = "SELECT * FROM projects"
    try:
      cursor.execute(query)
      projects = cursor.fetchall()
      if projects:
        projects_list = [
          {
            "id": project[0], 
            "username": project[1], 
            "title": project[2],
            "summary": project[3],
            # Convert JSON string to list format
            "steps": json.loads(project[4]),
            "status": project[5]
          } 
          for project in projects
        ]
        # 200 OK: For a successful request that returns data
        return jsonify(projects_list), 200
      else:
        # 404 Not Found: Projects not found
        return jsonify({"error": "No projects found"}), 404
    except mysql.connector.Error as e:
      # 500 Internal Server Error: Generic server-side failures
      return jsonify({"error": str(e)}), 500
    finally:
      # Close resources
      cursor.close()
      connection.close()
  # 500 Internal Server Error: Generic server-side failures
  return jsonify({"error": "Failed to connect to database"}), 500

# CREATE PROJECT
# TODO: add jwt_required, test
@app.route('/project/create', methods=['POST'])
@jwt_required()
def create_project():
  data = request.get_json()
  username = data['username']
  title = data['title']
  summary = data['summary']
  # Convert list to JSON string
  steps = json.dumps(data['steps']) 
  status = data['status']
  connection = get_db_connection()
  if connection:
    cursor = connection.cursor()
    query = "INSERT INTO projects (username, title, summary, steps, status) VALUES (%s, %s, %s, %s, %s)"
    try:
      cursor.execute(query, (username, title, summary, steps, status))
      # Commit changes
      connection.commit()
      response = jsonify({"message": "Project creation successful"})
      # 201 Created: User added/created successfully
      return response, 201
    except IntegrityError as e:
      # 400 Bad Request: Project already exists
      return jsonify({"error": "Project already exists."}), 400
    finally:
      # Close resources
      cursor.close()
      connection.close()
  # 500 Internal Server Error: Generic server-side failures
  return jsonify({"error": "Failed to connect to database"}), 500
  
create_users_table()
create_projects_table()
  
if __name__ == "__main__":
  app.run(debug=True)
