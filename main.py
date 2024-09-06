import os
from flask import Flask, request, jsonify
import mysql.connector
from mysql.connector import errorcode, IntegrityError
from dotenv import load_dotenv

app = Flask(__name__)

@app.route("/")
def hello_world():
    return "Hello world!"

load_dotenv()

print(os.getenv("ADMIN_USER"))
print(os.getenv("ADMIN_PASSWORD"))
print(os.getenv("ENDPOINT"))

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

@app.route('/user', methods=['POST'])
def add_user():
  data = request.get_json()
  username = data['username']
  password = data['password']
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

if __name__ == "__main__":
  create_users_table()
  app.run(debug=True)
