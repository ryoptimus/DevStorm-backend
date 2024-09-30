# db.py
import os
import mysql.connector
from mysql.connector import IntegrityError

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
      # cursor.execute("DROP TABLE IF EXISTS projects;")
      # print("Finished dropping 'projects' table (if existed).")
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