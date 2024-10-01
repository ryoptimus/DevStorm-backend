# task_routes.py

import mysql.connector
from mysql.connector import IntegrityError
from flask import Blueprint, jsonify, request
from db import get_db_connection

task_bp = Blueprint('task_bp', __name__)

# GET ALL TASKS
@task_bp.route('/task', methods=['GET'])
def get_all_tasks():
  connection = get_db_connection()
  if connection:
    cursor = connection.cursor()
    query = "SELECT * FROM tasks"
    try:
      cursor.execute(query)
      tasks = cursor.fetchall()
      if tasks:
        tasks_list = [
          {
            "id": task[0], 
            "pid": task[1], 
            "description": task[2],
            "priority": task[3],
            "status": task[4]
          } 
          for task in tasks
        ]
        # 200 OK: For a successful request that returns data
        return jsonify(tasks_list), 200
      else:
        # 404 Not Found: Tasks not found
        return jsonify({"error": "No tasks found"}), 404
    except mysql.connector.Error as e:
      # 500 Internal Server Error: Generic server-side failures
      return jsonify({"error": str(e)}), 500
    finally:
      # Close resources
      cursor.close()
      connection.close()
  # 500 Internal Server Error: Generic server-side failures
  return jsonify({"error": "Failed to connect to database"}), 500

# GET ALL TASKS for a given project
@task_bp.route('/task/<int:pid>', methods=['GET'])
def get_project_tasks(pid):
  connection = get_db_connection()
  if connection:
    cursor = connection.cursor()
    # Structure query, retrieve user
    query = "SELECT * FROM tasks WHERE pid = %s"
    cursor.execute(query, (pid,))
    tasks = cursor.fetchall()
    if tasks:
      tasks_list = [
          {
            "id": task[0], 
            "pid": task[1], 
            "description": task[2],
            "priority": task[3],
            "status": task[4]
          } 
          for task in tasks
        ]
      # 200 OK: For a successful request that returns data
      return jsonify(tasks_list), 200
    else:
      # 404 Not Found: Tasks not found
      return jsonify({"error": f"No tasks found for project with ID {pid}"}), 404
  
# CREATE TASK
@task_bp.route('/task/create', methods=['POST'])
def create_task():
  data = request.get_json()
  pid = data['pid']
  description = data['description']
  priority = data['priority']
  status = data['status']
  connection = get_db_connection()
  if connection:
    cursor = connection.cursor()
    query = "INSERT INTO tasks (pid, description, priority, status) VALUES (%s, %s, %s, %s)"
    try:
      cursor.execute(query, (pid, description, priority, status))
      # Commit changes
      connection.commit()
      response = jsonify({"message": "Task creation successful"})
      # 201 Created: User added/created successfully
      return response, 201
    except IntegrityError as e:
      # 400 Bad Request: Task already exists
      return jsonify({"error": "Task already exists."}), 400
    finally:
      # Close resources
      cursor.close()
      connection.close()
  # 500 Internal Server Error: Generic server-side failures
  return jsonify({"error": "Failed to connect to database"}), 500

# DELETE TASK
# Takes unique task's ID as parameter
@task_bp.route('/task/<int:id>/delete', methods=['DELETE'])
def delete_task(id):
  connection = get_db_connection()
  if connection:
    try:
      cursor = connection.cursor()
      query = "DELETE FROM tasks WHERE id = %s"
      cursor.execute(query, (id,))
      # Commit changes
      connection.commit()
      # 200 OK: For a successful request
      return jsonify({"message": "Task deleted successfully."}), 200
    except mysql.connector.Error as e:
      # 500 Internal Server Error
      return jsonify({"error": f"Database error: {e}"}), 500
    finally:
      # Close resources
      cursor.close()
      connection.close()
  # 500 Internal Server Error: Generic server-side failures
  return jsonify({"error": "Failed to connect to database"}), 500
