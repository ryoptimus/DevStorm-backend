# task_routes.py

import mysql.connector
from mysql.connector import IntegrityError
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
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

@task_bp.route('/task/<int:id>/get', methods=['GET'])
@jwt_required()
def get_task(id):
  username = get_jwt_identity()
  connection = get_db_connection()
  if connection:
    cursor = connection.cursor()
    # First, fetch task to acquire its project ID for authorization
    query_a = "SELECT * FROM tasks WHERE id = %s"
    try:
      cursor.execute(query_a, (id,))
      task = cursor.fetchone()
      if task:
        # Authorize that the current user matches the user listed as project owner
        query_b = "SELECT * FROM projects WHERE id = %s AND owner = %s"
        cursor.execute(query_b, (task[1], username))
        project = cursor.fetchone()
        if project:
          task_data = {
            "id": task[0], 
            "pid": task[1], 
            "description": task[2],
            "priority": task[3],
            "status": task[4]
          }
          # 200 OK: For a successful request that returns data
          return jsonify(task_data), 200
        else:
          # Return 403 Forbidden: Project exists (else the task would not exist), but
          # does not belong to the current user
          return jsonify({"error": "You do not have permission to access this project."}), 403
      else:
        # 404 Not Found: Task not found
        return jsonify({"error": f"No task found with ID {id}"}), 404
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
@jwt_required()
def get_project_tasks(pid):
  username = get_jwt_identity()
  connection = get_db_connection()
  if connection:
    cursor = connection.cursor()
    # Structure query, retrieve tasks
    query_a = "SELECT * FROM tasks WHERE pid = %s"
    cursor.execute(query_a, (pid,))
    tasks = cursor.fetchall()
    if tasks:
      task = tasks[0]
      # Authorize that the current user matches the user listed as project owner
      query_b = "SELECT * FROM projects WHERE id = %s AND owner = %s"
      cursor.execute(query_b, (task[1], username))
      project = cursor.fetchone()
      if project:
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
        # Return 403 Forbidden: Project exists (else the task would not exist), but
        # does not belong to the current user
        return jsonify({"error": "You do not have permission to access this project."}), 403
    else:
      # 404 Not Found: Tasks not found
      return jsonify({"error": f"No tasks found for project with ID {pid}"}), 404
  # 500 Internal Server Error: Generic server-side failures
  return jsonify({"error": "Failed to connect to database"}), 500
  
# CREATE TASK
@task_bp.route('/task/<int:pid>/create', methods=['POST'])
@jwt_required()
def create_task(pid):
  username = get_jwt_identity()
  data = request.get_json()
  description = data['description']
  priority = data['priority']
  status = data['status']
  connection = get_db_connection()
  if connection:
    cursor = connection.cursor()
    try:
      # Authorize that the current user matches the user listed as project owner
      query_a = "SELECT * FROM projects WHERE id = %s AND owner = %s"
      cursor.execute(query_a, (pid, username))
      project = cursor.fetchone()
      if project:
        query_b = "INSERT INTO tasks (pid, description, priority, status) VALUES (%s, %s, %s, %s)"
        cursor.execute(query_b, (pid, description, priority, status))
        # Commit changes
        connection.commit()
        response = jsonify({"message": "Task creation successful"})
        # 201 Created: User added/created successfully
        return response, 201
      else:
          # Return 403 Forbidden: Project exists (else the task would not exist), but
          # does not belong to the current user
          return jsonify({"error": "You do not have permission to access this project."}), 403
    except IntegrityError as e:
      # 400 Bad Request: Task already exists
      return jsonify({"error": "Task already exists."}), 400
    finally:
      # Close resources
      cursor.close()
      connection.close()
  # 500 Internal Server Error: Generic server-side failures
  return jsonify({"error": "Failed to connect to database"}), 500

@task_bp.route('/task/<int:id>/update-status', methods=['PUT'])
@jwt_required()
def update_task_status(id):
  username = get_jwt_identity()
  data = request.get_json()
  status = data['status']
  connection = get_db_connection()
  if connection:
    cursor = connection.cursor()
    try:
      # First, fetch task to acquire its project ID for authorization
      query_a = "SELECT * FROM tasks WHERE id = %s"
      cursor.execute(query_a, (id,))
      task = cursor.fetchone()
      if task:
        # Authorize that the current user matches the user listed as project owner
        query_b = "SELECT * FROM projects WHERE id = %s AND owner = %s"
        cursor.execute(query_b, (task[1], username))
        project = cursor.fetchone()
        if project:
          query_c = "UPDATE tasks SET status = %s WHERE id = %s"
          cursor.execute(query_c, (status, id))
          # Commit changes
          connection.commit()
          # 200 OK: For a successful request
          return jsonify({"message": "Task updated successfully."}), 200
        else:
          # Return 403 Forbidden: Project exists (else the task would not exist), but
          # does not belong to the current user
          return jsonify({"error": "You do not have permission to access this project."}), 403
      else:
        # 404 Not Found: Task not found
        return jsonify({"error": f"No task found with ID {id}"}), 404
    except mysql.connector.Error as e:
      # 500 Internal Server Error
      return jsonify({"error": f"Database error: {e}"}), 500
    finally:
      # Close resources
      cursor.close()
      connection.close()
  # 500 Internal Server Error: Generic server-side failures
  return jsonify({"error": "Failed to connect to database"}), 500

@task_bp.route('/task/<int:id>/update-description', methods=['PUT'])
@jwt_required()
def update_task_description(id):
  username = get_jwt_identity()
  data = request.get_json()
  description = data['description']
  connection = get_db_connection()
  if connection:
    cursor = connection.cursor()
    try:
      # First, fetch task to acquire its project ID for authorization
      query_a = "SELECT * FROM tasks WHERE id = %s"
      cursor.execute(query_a, (id,))
      task = cursor.fetchone()
      if task:
        # Authorize that the current user matches the user listed as project owner
        query_b = "SELECT * FROM projects WHERE id = %s AND owner = %s"
        cursor.execute(query_b, (task[1], username))
        project = cursor.fetchone()
        if project:
          query_c = "UPDATE tasks SET description = %s WHERE id = %s"
          cursor.execute(query_c, (description, id))
          # Commit changes
          connection.commit()
          # 200 OK: For a successful request
          return jsonify({"message": "Task updated successfully."}), 200
        else:
          # Return 403 Forbidden: Project exists (else the task would not exist), but
          # does not belong to the current user
          return jsonify({"error": "You do not have permission to access this project."}), 403
      else:
        # 404 Not Found: Task not found
        return jsonify({"error": f"No task found with ID {id}"}), 404
    except mysql.connector.Error as e:
      # 500 Internal Server Error
      return jsonify({"error": f"Database error: {e}"}), 500
    finally:
      # Close resources
      cursor.close()
      connection.close()
  # 500 Internal Server Error: Generic server-side failures
  return jsonify({"error": "Failed to connect to database"}), 500

# DELETE TASK
# Takes unique task's ID as parameter
@task_bp.route('/task/<int:id>/delete', methods=['DELETE'])
@jwt_required()
def delete_task(id):
  username = get_jwt_identity()
  connection = get_db_connection()
  if connection:
    cursor = connection.cursor()
    try:
      # First, fetch task to acquire its project ID for authorization
      query_a = "SELECT * FROM tasks WHERE id = %s"
      cursor.execute(query_a, (id,))
      task = cursor.fetchone()
      if task:
        # Authorize that the current user matches the user listed as project owner
        query_b = "SELECT * FROM projects WHERE id = %s AND owner = %s"
        cursor.execute(query_b, (task[1], username))
        project = cursor.fetchone()
        if project:
          query_c = "DELETE FROM tasks WHERE id = %s"
          cursor.execute(query_c, (id,))
          # Commit changes
          connection.commit()
          # 200 OK: For a successful request
          return jsonify({"message": "Task deleted successfully."}), 200
        else:
          # Return 403 Forbidden: Project exists (else the task would not exist), but
          # does not belong to the current user
          return jsonify({"error": "You do not have permission to access this project."}), 403
      else:
        # 404 Not Found: Project not found
        return jsonify({"error": f"No task found with ID {id}"}), 404
    except mysql.connector.Error as e:
      # 500 Internal Server Error
      return jsonify({"error": f"Database error: {e}"}), 500
    finally:
      # Close resources
      cursor.close()
      connection.close()
  # 500 Internal Server Error: Generic server-side failures
  return jsonify({"error": "Failed to connect to database"}), 500
