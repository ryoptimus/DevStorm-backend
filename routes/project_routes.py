# project_routes.py

import json
import mysql.connector
from flask import Blueprint, jsonify, request
from db import get_db_connection
from mysql.connector import IntegrityError
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
from helpers import engineer_taskgen_prompt
from routes.ai_routes import prompt_ai_to_generate_tasks

project_bp = Blueprint('project_bp', __name__)

# GET ALL PROJECTS
@project_bp.route('/project', methods=['GET'])
def get_all_projects():
  connection = get_db_connection()
  if connection:
    try:
      cursor = connection.cursor()
      query = "SELECT * FROM projects"
      cursor.execute(query)
      projects = cursor.fetchall()
      if projects:
        projects_list = [
          {
            "id": project[0], 
            "owner": project[1], 
            "collaborator1": project[2],
            "collaborator2": project[3],
            "title": project[4],
            "summary": project[5],
            # Convert JSON strings to list format
            "steps": json.loads(project[6]),
            "languages": json.loads(project[7]),
            "status": project[8],
            "date_created": project[9]
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

@project_bp.route('/project/<int:id>', methods=['GET'])
@jwt_required()
def get_project(id):
  username = get_jwt_identity()
  connection = get_db_connection()
  if connection:
    try:
      cursor = connection.cursor()
      query_a = "SELECT * FROM projects WHERE id = %s"
      cursor.execute(query_a, (id,))
      project = cursor.fetchone()
      if not project:
        # 404 Not Found: Project not found
        return jsonify({"error": f"No project found with ID {id}"}), 404
      
      # Structure query, retrieve project
      query_b = "SELECT * FROM projects WHERE id = %s AND owner = %s"
      cursor.execute(query_b, (id, username))
      project = cursor.fetchone()
      if not project:
        # 403 Forbidden: Project exists, but does not belong to the user
        return jsonify({"error": f"Project ID {id} does not belong to user {username}"}), 403

      project_data = {
        "id": project[0], 
        "owner": project[1], 
        "collaborator1": project[2],
        "collaborator2": project[3],
        "title": project[4],
        "summary": project[5],
        # Convert JSON strings to list format
        "steps": json.loads(project[6]),
        "languages": json.loads(project[7]),
        "status": project[8],
        "date_created": project[9]
      }
      # 200 OK: For a successful request that returns data
      return jsonify(project_data), 200
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
#TODO: return both projects that this user owns and those that this user collabs on
@project_bp.route('/project/by-user', methods=['GET'])
@jwt_required()
def get_user_projects():
    username = get_jwt_identity()
    connection = get_db_connection()
    if connection: 
      try:
        cursor = connection.cursor()
        # Structure query, retrieve user
        query = "SELECT * FROM projects WHERE owner = %s"
        cursor.execute(query, (username,))
        projects = cursor.fetchall()
        if projects:
          projects_list = [
            {
              "id": project[0], 
              "owner": project[1], 
              "collaborator1": project[2],
              "collaborator2": project[3],
              "title": project[4],
              "summary": project[5],
              # Convert JSON strings to list format
              "steps": json.loads(project[6]),
              "languages": json.loads(project[7]),
              "status": project[8],
              "date_created": project[9]
            } 
            for project in projects
          ]
          # 200 OK: For a successful request that returns data
          return jsonify(projects_list), 200
        else:
          # Return empty list and 200 OK: Request successful but
          # no projects found
          return jsonify([]), 200
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
@project_bp.route('/project/create', methods=['POST'])
@jwt_required()
def create_project():
  data = request.get_json()
  username = get_jwt_identity()
  title = data['title']
  summary = data['summary']
  steps = data['steps'] 
  languages = data['languages']
  date_created = datetime.now()
  connection = get_db_connection()
  if connection:
    try:
      cursor = connection.cursor()
      query_a = "SELECT * FROM users WHERE username = %s"
      cursor.execute(query_a, (username,))
      user = cursor.fetchone()
      if user[7] != user[8]:
        # 409 Conflict: User-side error in request
        return jsonify({"error": f"User {username} already has project in progress. User must complete existing project before creating a new one"}), 409
      query_b = "INSERT INTO projects (owner, title, summary, steps, languages, date_created) VALUES (%s, %s, %s, %s, %s, %s)"
      # Convert 'steps' list to JSON string for storage
      cursor.execute(query_b, (username, title, summary, json.dumps(steps), json.dumps(languages), date_created))
      # Retrieve last inserted project ID (pid)
      pid = cursor.lastrowid
      # Commit changes
      connection.commit()
      # Generate tasks lists for each project step
      tasks_lists = prompt_ai_to_generate_tasks(engineer_taskgen_prompt(title, summary, languages, steps))
      # Structure task insertion query
      query_c = "INSERT INTO tasks (pid, description, priority, status) VALUES (%s, %s, %s, %s)"
      # Enumerate starting from 1 to extract priority based on step number
      for priority, tasks_list in enumerate(tasks_lists, start=1):
        # Get tasks_list for each step, defaulting to empty list if not found
        for task in tasks_list.get('tasks', []):
          # Execute query. Status is default 1 to indicate it is "to-do"
          cursor.execute(query_c, (pid, task, priority, 1))
      # Commit changes
      connection.commit()
      query_d = "UPDATE users SET projects = projects + 1 WHERE username = %s"
      cursor.execute(query_d, (username,))
      # Commit changes
      connection.commit()
      response = jsonify({"message": "Project, tasks creation successful"})
      # 201 Created: Project added/created successfully
      return response, 201
    except IntegrityError as e:
      # Roll back changes if error occurs
      connection.rollback()
      # 400 Bad Request: Project creation failed
      return jsonify({"error": "Project creation failed."}), 400
    finally:
      # Close resources
      cursor.close()
      connection.close()
  # 500 Internal Server Error: Generic server-side failures
  return jsonify({"error": "Failed to connect to database"}), 500

# UPDATE
# Add a collaborator
@project_bp.route('/project/<int:id>/add-collaborator', methods=['PUT'])
@jwt_required()
def add_project_collaborator(id):
  data = request.get_json()
  username = get_jwt_identity()
  new_collaborator = data['collaborator']
  connection = get_db_connection()
  if connection:
    try:
      cursor = connection.cursor()
      # Check if project exists
      query_a = "SELECT * FROM projects WHERE id = %s"
      cursor.execute(query_a, (id,))
      project = cursor.fetchone()
      if not project:
        # 404 Not Found: Project not found
        return jsonify({"error": f"No project found with ID {id}"}), 404
      
      # Check if existing project lists current user as owner
      query_b = "SELECT * FROM projects WHERE id = %s AND owner = %s"
      cursor.execute(query_b, (id, username))
      project = cursor.fetchone()
      if not project:
        # 403 Forbidden: Project exists, but does not belong to the user
        return jsonify({"error": f"Project ID {id} does not belong to user {username}"}), 403
      
      collaborator1 = project[2]
      collaborator2 = project[3]
      if collaborator1 is not None:
        if collaborator2 is not None:
          # 400 Bad Request: Project already has two collaborators
          return jsonify({"error": f"Project already has two collaborators."}), 400
        else:
          # Update project status
          query_c = "UPDATE projects SET collaborator2 = %s WHERE id = %s"
      else:
        query_c = "UPDATE projects SET collaborator1 = %s WHERE id = %s"
      
      cursor.execute(query_c, (new_collaborator, id))
      
      connection.commit()
      # 200 OK: For a successful request
      return jsonify({"message": "Project collaborator updated successfully"}), 200
    except IntegrityError as e:
      # 403 Forbidden: Proposed collaborator does not exist
      return jsonify({"error": f"The user {new_collaborator} does not exist."}), 403
    finally:
      # Close resources
      cursor.close()
      connection.close()
  # 500 Internal Server Error: Generic server-side failures
  return jsonify({"error": "Failed to connect to database"}), 500

# # UPDATE COLLABORATOR
# @project_bp.route('/project/<int:id>/update-collaborator', methods=['PUT'])
# @jwt_required()
# def update_project_collaborator(id):
#   data = request.get_json()
#   username = get_jwt_identity()
#   new_collaborator = data['collaborator']
#   connection = get_db_connection()
#   if connection:
#     try:
#       cursor = connection.cursor()
#       # Check if project exists
#       query_a = "SELECT * FROM projects WHERE id = %s"
#       cursor.execute(query_a, (id,))
#       project = cursor.fetchone()
#       if not project:
#         # 404 Not Found: Project not found
#         return jsonify({"error": f"No project found with ID {id}"}), 404
      
#       # Check if existing project lists current user as owner
#       query_b = "SELECT * FROM projects WHERE id = %s AND owner = %s"
#       cursor.execute(query_b, (id, username))
#       project = cursor.fetchone()
#       if not project:
#         # 403 Forbidden: Project exists, but does not belong to the user
#         return jsonify({"error": f"Project ID {id} does not belong to user {username}"}), 403
      
#       # Update project status
#       query_c = "UPDATE projects SET collaborator = %s WHERE id = %s"
#       cursor.execute(query_c, (new_collaborator, id))
      
#       connection.commit()
#       # 200 OK: For a successful request
#       return jsonify({"message": "Project collaborator updated successfully"}), 200
#     except IntegrityError as e:
#       # 403 Forbidden: Proposed collaborator does not exist
#       return jsonify({"error": f"The user {new_collaborator} does not exist."}), 403
#     finally:
#       # Close resources
#       cursor.close()
#       connection.close()
#   # 500 Internal Server Error: Generic server-side failures
#   return jsonify({"error": "Failed to connect to database"}), 500

# UPDATE
@project_bp.route('/project/<int:id>/remove-collaborator', methods=['PUT'])
@jwt_required()
def remove_project_collaborator(id):
  username = get_jwt_identity()
  data = request.get_json()
  collaborator = data['collaborator']
  connection = get_db_connection()
  if connection:
    try:
      cursor = connection.cursor()
      # Check if project exists
      query_a = "SELECT * FROM projects WHERE id = %s"
      cursor.execute(query_a, (id,))
      project = cursor.fetchone()
      if not project:
        # 404 Not Found: Project not found
        return jsonify({"error": f"No project found with ID {id}"}), 404
      
      query_b = "SELECT * FROM projects WHERE id = %s AND owner = %s"
      cursor.execute(query_b, (id, username))
      project = cursor.fetchone()
      if not project:
        # 403 Forbidden: Project exists, but does not belong to the user
        return jsonify({"error": f"Project ID {id} does not belong to user {username}"}), 403
      
      collaborator1 = project[2]
      collaborator2 = project[3]
      if collaborator1 is not None and collaborator == collaborator1:
        query_c = "UPDATE projects SET collaborator1 = %s WHERE id = %s"
      elif collaborator2 is not None and collaborator == collaborator2:
        query_c = "UPDATE projects SET collaborator2 = %s WHERE id = %s"
      elif collaborator1 is None and collaborator2 is None:
        return jsonify({"message": "This project has no collaborators to remove!"}), 400
      else:
        return jsonify({"message": f"Collaborator '{collaborator}' was not listed on this project"}), 400
      
      cursor.execute(query_c, (None, id))
      
      connection.commit()
      # 200 OK: For a successful request
      return jsonify({"message": "Project collaborator updated successfully"}), 200
    except mysql.connector.Error as e:
      # 500 Internal Server Error
      return jsonify({"error": f"Database error: {e}"}), 500
    finally:
      # Close resources
      cursor.close()
      connection.close()
  # 500 Internal Server Error: Generic server-side failures
  return jsonify({"error": "Failed to connect to database"}), 500
  

# UPDATE
# Toggle status of a given project
@project_bp.route('/project/<int:id>/update-status', methods=['PUT'])
@jwt_required()
def update_project_status(id):
  username = get_jwt_identity()
  connection = get_db_connection()
  if connection:
    try:
      cursor = connection.cursor()
      # Check if project exists
      query_a = "SELECT * FROM projects WHERE id = %s"
      cursor.execute(query_a, (id,))
      project = cursor.fetchone()
      if not project:
        # 404 Not Found: Project not found
        return jsonify({"error": f"No project found with ID {id}"}), 404
      
      # Check if existing project lists current user as owner
      query_b = "SELECT * FROM projects WHERE id = %s AND owner = %s"
      cursor.execute(query_b, (id, username))
      project = cursor.fetchone()
      if not project:
        # 403 Forbidden: Project exists, but does not belong to the user
        return jsonify({"error": f"Project ID {id} does not belong to user {username}"}), 403
      
      project_status = project[8]
      print(f"Project ID {id} current status: {project_status}")
      # Prepare queries to update user's project completion count
      if project_status == 0:
        new_status = 1
        query_d = "UPDATE users SET projects_completed = projects_completed + 1 WHERE username = %s"
      else:
        new_status = 0
        query_d = "UPDATE users SET projects_completed = projects_completed - 1 WHERE username = %s"

      # Update project status
      query_c = "UPDATE projects SET status = %s WHERE id = %s"
      cursor.execute(query_c, (new_status, id))
      # Update user's project completion count
      cursor.execute(query_d, (username,))    
      # Commit both changes together
      connection.commit()
      # 200 OK: For a successful request
      return jsonify({"message": "Project status updated successfully"}), 200
    except mysql.connector.Error as e:
      # 500 Internal Server Error
      return jsonify({"error": f"Database error: {e}"}), 500
    finally:
      # Close resources
      cursor.close()
      connection.close()
  # 500 Internal Server Error: Generic server-side failures
  return jsonify({"error": "Failed to connect to database"}), 500

# DELETE PROJECT
@project_bp.route('/project/<int:id>/delete', methods=['DELETE'])
@jwt_required()
def delete_project(id):
  username = get_jwt_identity()
  connection = get_db_connection()
  if connection:
    try:
      cursor = connection.cursor()
      # Check if project exists
      query_a = "SELECT * FROM projects WHERE id = %s"
      cursor.execute(query_a, (id,))
      project = cursor.fetchone()
      if not project:
        # 404 Not Found: Project not found
        return jsonify({"error": f"No project found with ID {id}"}), 404
      
      query_b = "SELECT * FROM projects WHERE id = %s AND owner = %s"
      cursor.execute(query_b, (id, username))
      project = cursor.fetchone()
      if not project:
        # 403 Forbidden: Project exists, but does not belong to the user
        return jsonify({"error": f"Project ID {id} does not belong to user {username}"}), 403
      
      # Delete tasks first, as they are linked to project through pid 
      query_c = "DELETE FROM tasks where pid = %s"
      cursor.execute(query_c, (id,))
      # Delete project
      query_d = "DELETE FROM projects WHERE id = %s"
      cursor.execute(query_d, (id,))
      
      query_e = "UPDATE users SET projects = projects - 1 WHERE username = %s"
      cursor.execute(query_e, (username,))
      if project[8] == 1:
        query_f = "UPDATE users SET projects_completed = projects_completed - 1 WHERE username = %s"
        cursor.execute(query_f, (username,))
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

