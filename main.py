import os
import json
from flask import request, jsonify
import mysql.connector
from mysql.connector import IntegrityError
from groq import Groq
from flask_jwt_extended import (
    create_access_token, create_refresh_token,
    jwt_required, get_jwt, get_jwt_identity, set_access_cookies, set_refresh_cookies,
    unset_jwt_cookies, verify_jwt_in_request
)
from datetime import datetime
from app import create_app
from db import get_db_connection, create_users_table, create_projects_table, create_tasks_table
from helpers import engineer_brainstorm_prompt, engineer_taskgen_prompt, hash_password, verify_password, ProjectIdea

app, jwt, bcrypt = create_app()

# Create blocklist
blocklist = set()

@app.route("/")
def hello_world():
    return "Hello world!"

#TODO: Make 'projects' a list format of PIDs
@app.route('/user/<username>', methods=['GET'])
def get_user(username):
  connection = get_db_connection()
  if connection:
    cursor = connection.cursor()
    query = "SELECT * FROM users WHERE username = %s"
    try:
      cursor.execute(query, (username,))
      # Check that cursor did not return none
      user = cursor.fetchone()
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
    except mysql.connector.Error as e:
      # 500 Internal Server Error: Generic server-side failures
      return jsonify({"error": str(e)}), 500
    finally:
      # Close resources
      cursor.close()
      connection.close()
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
  prompt = engineer_brainstorm_prompt(roles, technologies, industries)
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
  
@app.route('/project/<int:id>', methods=['GET'])
def get_project(id):
  connection = get_db_connection()
  if connection:
    cursor = connection.cursor()
    # Structure query, retrieve project
    query = "SELECT * FROM projects WHERE id = %s"
    try:
      cursor.execute(query, (id,))
      project = cursor.fetchone()
      if project:
        project_data = {
          "id": project[0], 
          "username": project[1], 
          "title": project[2],
          "summary": project[3],
          # Convert JSON string to list format
          "steps": json.loads(project[4]),
          "status": project[5]
        }
        # 200 OK: For a successful request that returns data
        return jsonify(project_data), 200
      else:
        # 404 Not Found: Projects not found
        return jsonify({"error": f"No project found with ID {id}"}), 404
    except mysql.connector.Error as e:
      # 500 Internal Server Error: Generic server-side failures
      return jsonify({"error": str(e)}), 500
    finally:
      # Close resources
      cursor.close()
      connection.close()
  # 500 Internal Server Error: Generic server-side failures
  return jsonify({"error": "Failed to connect to database"}), 500 

# GET ALL PROJECTS for a given user
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
      return jsonify({"error": f"No projects found for user '{username}'"}), 404

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
@app.route('/project/create', methods=['POST'])
@jwt_required()
def create_project():
  data = request.get_json()
  username = data['username']
  title = data['title']
  summary = data['summary']
  steps = data['steps'] 
  status = data['status']
  connection = get_db_connection()
  if connection:
    cursor = connection.cursor()
    query = "INSERT INTO projects (username, title, summary, steps, status) VALUES (%s, %s, %s, %s, %s)"
    try:
      # Convert 'steps' list to JSON string for storage
      cursor.execute(query, (username, title, summary, json.dumps(steps), status))
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

# DELETE PROJECT
@app.route('/project/<int:id>/delete', methods=['DELETE'])
def delete_project(id):
  connection = get_db_connection()
  if connection:
    try:
      cursor = connection.cursor()
      query = "DELETE FROM projects WHERE id = %s"
      cursor.execute(query, (id,))
      # Commit changes
      connection.commit()
      # 200 OK: For a successful request
      return jsonify({"message": "Project deleted successfully."}), 200
    except mysql.connector.Error as e:
      # 500 Internal Server Error
      return jsonify({"error": f"Database error: {e}"}), 500
    finally:
      # Close resources
      cursor.close()
      connection.close()
  # 500 Internal Server Error: Generic server-side failures
  return jsonify({"error": "Failed to connect to database"}), 500
  
create_users_table()
create_projects_table()
create_tasks_table()
  
if __name__ == "__main__":
  app.run(debug=True)
