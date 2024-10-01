# project_routes.py

import os
import json
import mysql.connector
from flask import Blueprint, jsonify, request
from db import get_db_connection
from mysql.connector import IntegrityError
from groq import Groq
from flask_jwt_extended import jwt_required, get_jwt_identity
from helpers import engineer_taskgen_prompt

project_bp = Blueprint('project_bp', __name__)

# GET ALL PROJECTS
@project_bp.route('/project', methods=['GET'])
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
            # Convert JSON strings to list format
            "steps": json.loads(project[4]),
            "languages": json.loads(project[5]),
            "status": project[6]
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
          # Convert JSON strings to list format
          "steps": json.loads(project[4]),
          "languages": json.loads(project[5]),
          "status": project[6]
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
@project_bp.route('/project/by-user', methods=['GET'])
def get_user_projects():
    username = get_jwt_identity()
    connection = get_db_connection()
    if connection:
        cursor = connection.cursor()
        # Structure query, retrieve user
        query = "SELECT * FROM projects WHERE username = %s"
        try:
            cursor.execute(query, (username,))
            projects = cursor.fetchall()
            if projects:
                projects_list = [
                    {
                        "id": project[0], 
                        "username": project[1], 
                        "title": project[2],
                        "summary": project[3],
                        # Convert JSON strings to list format
                        "steps": json.loads(project[4]),
                        "languages": json.loads(project[5]),
                        "status": project[6]
                    } 
                    for project in projects
                ]
                # 200 OK: For a successful request that returns data
                return jsonify(projects_list), 200
            else:
                # 404 Not Found: Projects not found
                return jsonify({"error": f"No projects found for user '{username}'"}), 404
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
  connection = get_db_connection()
  if connection:
    cursor = connection.cursor()
    query_a = "INSERT INTO projects (username, title, summary, steps, languages, status) VALUES (%s, %s, %s, %s, %s, %s)"
    try:
      # Convert 'steps' list to JSON string for storage
      cursor.execute(query_a, (username, title, summary, json.dumps(steps), json.dumps(languages), 0))
      # Retrieve last inserted project ID (pid)
      pid = cursor.lastrowid
      # Commit changes
      connection.commit()
      # Generate tasks lists for each project step
      tasks_lists = prompt_ai_to_generate_tasks(engineer_taskgen_prompt(title, summary, languages, steps))
      # Structure task insertion query
      query_b = "INSERT INTO tasks (pid, description, priority, status) VALUES (%s, %s, %s, %s)"
      # Enumerate starting from 1 to extract priority based on step number
      for priority, tasks_list in enumerate(tasks_lists, start=1):
        # Get tasks_list for each step, defaulting to empty list if not found
        for task in tasks_list.get('tasks', []):
          # Execute query. Status is default 1 to indicate it is "to-do"
          cursor.execute(query_b, (pid, task, priority, 1))
      # Commit changes
      connection.commit()
      response = jsonify({"message": "Project, tasks creation successful"})
      # 201 Created: Project added/created successfully
      return response, 201
    except IntegrityError as e:
      # 400 Bad Request: Project creation failed
      return jsonify({"error": "Project creation failed."}), 400
    finally:
      # Close resources
      cursor.close()
      connection.close()
  # 500 Internal Server Error: Generic server-side failures
  return jsonify({"error": "Failed to connect to database"}), 500
  
# Helper function to generate tasks
def prompt_ai_to_generate_tasks(prompt):
  print(f"Prompt: {prompt}")
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
            "You are project assistant that provides task lists for each project step in JSON.\n"
            "The JSON object must use the schema: "
            "{'tasks_lists': [{'title': 'Step 1 title', 'tasks': ['task 1', 'task 2', 'task 3']}, ...]}"
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
    # print(f"Response: {response}")
    generated_text = response.choices[0].message.content
    print(f"Generated text: {generated_text}")
    parsed_response = json.loads(generated_text)
    # Extract 'tasks_lists' from parsed_response, defaulting to empty list if
    # not found
    tasks_lists = parsed_response.get('tasks_lists', [])
    # Return tasks_list
    return tasks_lists
  except Exception as e:
    # Log the error and return None
    print(f"Error in AI generation: {e}")
    return None

# DELETE PROJECT
@project_bp.route('/project/<int:id>/delete', methods=['DELETE'])
def delete_project(id):
  connection = get_db_connection()
  if connection:
    try:
      cursor = connection.cursor()
      query_a = "DELETE FROM tasks where pid = %s"
      cursor.execute(query_a, (id,))
      query_b = "DELETE FROM projects WHERE id = %s"
      cursor.execute(query_b, (id,))
      rows_affected = cursor.rowcount
      if rows_affected == 0:
        # 404 Not Found: Project not found
        return jsonify({"error": "Project not found."}), 404
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

