import os
from flask import Flask, request, jsonify, session
from flask_cors import CORS
import mysql.connector
from mysql.connector import errorcode, IntegrityError
from dotenv import load_dotenv
from groq import Groq
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
CORS(app, resources={r'/user': {'origins': 'http://localhost:3000'},
                     r'/register': {'origins': 'http://localhost:3000'},
                     r'/prompt': {'origins': 'http://localhost:3000'}})

@app.route("/")
def hello_world():
    return "Hello world!"

load_dotenv()

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

@app.route('/register', methods=['POST'])
def register_user():
  data = request.get_json()
  username = data['username']
  password = generate_password_hash(data['password'])
  connection = get_db_connection()
  if connection:
    cursor = connection.cursor()
    query = "INSERT INTO users (username, password) VALUES (%s, %s)"
    try:
      cursor.execute(query, (username, password,))
      connection.commit()
      # 201 Created: User added/created successfully
      return jsonify({"message": "User added successfully."}), 201
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
      # 200 OK: For a successful request that returns data
      return jsonify({"id": user[0], "username": user[1], "password": user[2]}), 200
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
        users_list = [{"id": user[0], "username": user[1], "password": user[2]} for user in users]
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

@app.route('/login', methods=['POST'])
def login():
  data = request.get_json()
  username = data['username']
  password = data['password']
    
  connection = get_db_connection()
  if connection:
    cursor = connection.cursor()
    query = "SELECT * FROM users WHERE username = %s"
    cursor.execute(query, (username,))
    user = cursor.fetchone()
    if user and check_password_hash(user['password'], password):
      session['user_id'] = user['id']
      # 200 OK: For a successful request
      return jsonify({"message": "Login verified"}), 200
    else:
      # 401 Unauthorized: Request lacks valid authentication credentials
      return jsonify({"error": "Invalid credentials"}), 401
  # 500 Internal Server Error: Generic server-side failures
  return jsonify({"error": "Failed to connect to database"}), 500

@app.route('/prompt', methods=['POST'])
def prompt_ai():
  data = request.get_json()
  roles = data['role']
  technologies = data['technology']
  industries = data['industries']
  # print(engineer_prompt(roles, technologies, industries))
  prompt = engineer_prompt(roles, technologies, industries)
  if not data:
    # 400 Bad Request: No inputs provided
    return jsonify({"error": "No inputs provided"}), 400
  try:
    client = Groq(api_key=os.getenv("GROQ_KEY"),)
    response = client.chat.completions.create(
      messages =[
        {
          "role": "user",
          "content": prompt
        }
      ],
      model="llama3-8b-8192",
      max_tokens=150
    )
    generated_text = response.choices[0].message.content
    # print(response.choices[0].message.content)
    # 200 OK: For a successful request that returns data
    return jsonify({"response": generated_text}), 200
  except Exception as e:
    print(f"Error calling Groq API: {e}")
    # 500 Internal Server Error: Generic server-side failures
    return jsonify({"error": "Failed to call AI"}), 500
  
def engineer_prompt(roles, technologies, industries):
# ex.
# I am a role[0] and role[1] using technology[0] and technology[1] and technology[2] in the 
# industries[0] industry. Give me project ideas.
  if len(industries) > 1:
    prompt = "I am a " + conjunct_me([role.lower() for role in roles]) + " using " + conjunct_me(technologies) + " in the " + conjunct_me([industry.lower() for industry in industries]) + " industries. Give me project ideas."
  else:
    prompt = "I am a " + conjunct_me([role.lower() for role in roles]) + " using " + conjunct_me(technologies) + " in the " + conjunct_me([industry.lower() for industry in industries]) + " industry. Give me project ideas."
  return prompt

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
