import os
from flask import Flask, request
import mysql.connector
from mysql.connector import errorcode, IntegrityError
from dotenv import load_dotenv, dotenv_values

load_dotenv()

print(os.getenv("ADMIN_USER"))
print(os.getenv("ADMIN_PASSWORD"))
print(os.getenv("ENDPOINT"))

def create_users_table(connection):
   cursor = connection.cursor()
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
   
def insert_record(connection, username, password):
   cursor = connection.cursor()
   query = "INSERT INTO users (username, password) VALUES (%s, %s)"
   try:
      cursor.execute(query, (username, password))
      connection.commit()
      print("User added successfully.")
   except IntegrityError as e:
      if e.errno == errorcode.ER_DUP_ENTRY:
         print(f"Error: Username '{username}' already exists. Please choose a different one.")
      else:
         print(e)
   finally:
    cursor.close()

def update_record(connection, username, password, id):
   cursor = connection.cursor()
   query = "UPDATE users SET username = %s, password = %s WHERE id = %s"
   cursor.execute(query, (username, password, id))
   connection.commit()
   cursor.close()

def delete_record(connection, username):
   cursor = connection.cursor()
   query = "DELETE FROM users WHERE username = %s"
   cursor.execute(query, (username,))
   connection.commit()
   cursor.close()

def get_user(connection, username):
    cursor = connection.cursor()
    query = "SELECT * FROM users WHERE username = %s"
    cursor.execute(query, (username,))
    for item in cursor:
        print(item)
    cursor.close()

try:
    connection = mysql.connector.connect(user=os.getenv("ADMIN_USER"), password=os.getenv("ADMIN_PASSWORD"), host=os.getenv("ENDPOINT"), port=3306, database="flaskproject")
except mysql.connector.Error as err:
  if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
    print("Something is wrong with your user name or password")
  elif err.errno == errorcode.ER_BAD_DB_ERROR:
    print("Database does not exist")
  else:
    print(err)
else:
  create_users_table(connection)
  print("Created users table if did not exist")
  insert_record(connection, "flipjackbob", "flipjackedrob")
  print("Inserted record")
  insert_record(connection, "flipjackbob", "12345")
  print("Tried to insert duplicate")
  get_user(connection, "flipjackbob")
  print("User acquired")
  delete_record(connection, "flipjackbob")
  print("Deleted user")
  connection.close()
  print("Connexion clozed")


    

app = Flask(__name__)

@app.route("/")
def hello_world():
    return "Hello world!"

@app.route("/home2")
def home2():
    return "home2"