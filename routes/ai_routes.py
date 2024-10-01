# ai_routes.py

import os
import json
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from groq import Groq
from helpers import engineer_brainstorm_prompt, ProjectIdea

ai_bp = Blueprint('ai_bp', __name__)

# PROMPT
@ai_bp.route('/api/prompt', methods=['POST'])
# Ensure route /prompt can only be accessed by users with valid JWT
@jwt_required()
def prompt_ai_to_brainstorm_project_idea():
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