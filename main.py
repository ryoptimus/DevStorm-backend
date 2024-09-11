import os
import json
from flask import Flask, request, jsonify, session
from flask_cors import CORS
import mysql.connector
from mysql.connector import IntegrityError
from dotenv import load_dotenv
from groq import Groq
import hashlib
from flask_jwt_extended import create_access_token
from flask_jwt_extended import get_jwt_identity
from flask_jwt_extended import jwt_required
from flask_jwt_extended import JWTManager
from typing import List, Optional
from pydantic import BaseModel

load_dotenv()

app = Flask(__name__)
# Configure CORS
CORS(app, resources={r'/user': {'origins': 'http://localhost:3000'},
                     r'/register': {'origins': 'http://localhost:3000'},
                     r'/prompt': {'origins': 'http://localhost:3000'},
                     r'/login': {'origins': 'http://localhost:3000'}})


# Setup the Flask-JWT-Extended extension
app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY")
jwt = JWTManager(app)

@app.route("/")
def hello_world():
    return "Hello world!"

def get_db_connection():
  try:
    connection = mysql.connector.connect(
      user=os.getenv("ADMIN_USER"), 
      password=os.getenv("ADMIN_PASSWORD"), 
      host=os.getenv("ENDPOINT"), 
      port=3306, 
      database="flaskproject"
    )
    return connection
  except mysql.connector.Error as e:
    print(f"error: {e}")
    return None

def create_users_table():
  connection = get_db_connection()
  if connection:
    cursor = connection.cursor()
    try:
      # Drop previous table of same name if one exists
      cursor.execute("DROP TABLE IF EXISTS users;")
      print("Finished dropping table (if existed).")
      # Create table
      cursor.execute("""
          CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY, 
                username VARCHAR(50) UNIQUE, 
                password VARCHAR(32)
            );
        """)
      connection.commit()
      print("Users table created.")
    except mysql.connector.Error as e:
      print(f"Error creating table: {e}")
    finally:
      cursor.close()
      connection.close()
  else:
    print("Failed to connect to database. Could not create table.")

# REGISTER
@app.route('/register', methods=['POST'])
def register_user():
  data = request.get_json()
  username = data['username']
  password = data['password']
  hashed_password = hash_password(password)
  connection = get_db_connection()
  if connection:
    cursor = connection.cursor()
    query = "INSERT INTO users (username, password) VALUES (%s, %s)"
    try:
      cursor.execute(query, (username, hashed_password,))
      connection.commit()
      access_token = create_access_token(identity=username)
      response_data = {
        "message": "User added successfully",
        "access_token": access_token
      }
      # 201 Created: User added/created successfully
      return jsonify(response_data), 201
    except IntegrityError as e:
      # 400 Bad Request: Username already exists
      return jsonify({"error": "Username already exists."}), 400
    finally:
      cursor.close()
      connection.close()
  # 500 Internal Server Error: Generic server-side failures
  return jsonify({"error": "Failed to connect to database"}), 500

@app.route('/user/<username>', methods=['GET'])
def get_user(username):
  connection = get_db_connection()
  if connection:
    cursor = connection.cursor()
    query = "SELECT * FROM users WHERE username = %s"
    cursor.execute(query, (username,))
    # Check that cursor did not return none
    user = cursor.fetchone()
    cursor.close()
    connection.close()
    if user:
      user_data = {
        "id": user[0], 
        "username": user[1], 
        "password": user[2]
      }
      # 200 OK: For a successful request that returns data
      return jsonify(user_data), 200
    else:
      # 404 Not Found: User not found
      return jsonify({"error": "User not found"}), 404
  # 500 Internal Server Error: Generic server-side failures
  return jsonify({"error": "Failed to connect to database"}), 500

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
            "username": user[1], 
            "password": user[2]
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
      cursor.close()
      connection.close()
  # 500 Internal Server Error: Generic server-side failures
  return jsonify({"error": "Failed to connect to database"}), 500

# UPDATE
# Requires user ID
@app.route('/user/<int:id>', methods=['PUT'])
def update_record(id):
  data = request.get_json()
  username = data['username']
  password = data['password']
  connection = get_db_connection()
  if connection:
    cursor = connection.cursor()
    query = "UPDATE users SET username = %s, password = %s WHERE id = %s"
    cursor.execute(query, (username, password, id))
    connection.commit()
    cursor.close()
    connection.close()
    # 200 OK: For a successful request that returns data
    return jsonify({"message": "User updated successfully"}), 200
  # 500 Internal Server Error: Generic server-side failures
  return jsonify({"error": "Failed to connect to database"}), 500

# DELETE
@app.route('/user/<username>', methods=['DELETE'])
def delete_record(username):
  connection = get_db_connection()
  if connection:
    cursor = connection.cursor()
    query = "DELETE FROM users WHERE username = %s"
    cursor.execute(query, (username,))
    connection.commit()
    cursor.close()
    connection.close()
    # 200 OK: For a successful request that returns data
    return jsonify({"message": "User deleted successfully."}), 200
  # 500 Internal Server Error: Generic server-side failures
  return jsonify({"error": "Failed to connect to database"}), 500

# LOGIN
@app.route('/login', methods=['POST'])
def login():
  data = request.get_json()
  username = data['username']
  password = data['password']
  hashed_password = hash_password(password)
    
  connection = get_db_connection()
  if connection:
    cursor = connection.cursor()
    # Structure query, retrieve user
    query = "SELECT * FROM users WHERE username = %s"
    cursor.execute(query, (username,))
    user = cursor.fetchone()
    cursor.close()
    connection.close()
      
    stored_hash = user[2]
    if user and hashed_password == stored_hash:
      access_token = create_access_token(identity=username)
      response_data = {
        "message": "Login verified",
        "access_token": access_token
      }
      # 200 OK: For a successful request
      return jsonify(response_data), 200
    else:
      # 401 Unauthorized: Request lacks valid authentication credentials
      return jsonify({"error": "Invalid credentials"}), 401
  # 500 Internal Server Error: Generic server-side failures
  return jsonify({"error": "Failed to connect to database"}), 500

# PROMPT helper: data model for project idea generation
class ProjectIdea(BaseModel):
    project_title: str
    description: str
    steps: List[str]

# PROMPT
@app.route('/prompt', methods=['POST'])
# Ensure route /prompt can only be accessed by users with valid JWT
@jwt_required()
def prompt_ai():
  # Retrieve user identity from the JWT
  current_user = get_jwt_identity()
  print(f"{current_user} is authenticated.")
  
  data = request.get_json()
  roles = data['role']
  technologies = data['technology']
  industries = data['industries']
  prompt = engineer_prompt(roles, technologies, industries)
  print(prompt)
  if not data:
    # 400 Bad Request: No inputs provided
    return jsonify({"error": "No inputs provided"}), 400
  try:
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
    print(f"response.choices[0].message: {response.choices[0].message}")
    print(f"response.choices[0].message.content: {generated_text}")
    print(response.usage)
    # 200 OK: For a successful request that returns data
    return jsonify({"response": generated_text}), 200
  except Exception as e:
    print(f"Error calling Groq API: {e}")
    # 500 Internal Server Error: Generic server-side failures
    return jsonify({"error": "Failed to call AI"}), 500
  
def hash_password(password: str) -> str:
    # Hash a password using MD5
    return hashlib.md5(password.encode()).hexdigest()
  
def engineer_prompt(roles, technologies, industries):
  # Parse inputs lists to engineer prompt
  # Prompt example:
  #   I am a role[0] and role[1] using technology[0] and technology[1] and technology[2] in the 
  #   industries[0] industry. Generate a project idea.
  if len(industries) > 1:
    prompt = (
      "I am a " + conjunct_me([role.lower() for role in roles]) +
      " using " + conjunct_me(technologies) +
      " in the " + conjunct_me([industry.lower() for industry in industries]) +
      " industries. Generate a project idea."
    )
  else:
    prompt = (
      "I am a " + conjunct_me([role.lower() for role in roles]) +
      " using " + conjunct_me(technologies) +
      " in the " + conjunct_me([industry.lower() for industry in industries]) +
      " industry. Generate a project idea."
      )
  return prompt

# Conjoin list of things using commas and/or 'and'
def conjunct_me(list):
  if len(list) > 2:
    joined_string = ", ".join(list[:-1]) + ", and " + list[-1]
    return joined_string
  elif len(list) == 2:
    joined_string = " and ".join(list)
    return joined_string
  else:
    return list[0]
 
if __name__ == "__main__":
  create_users_table()
  app.run(debug=True)
