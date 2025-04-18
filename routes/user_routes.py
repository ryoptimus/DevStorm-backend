# user_routes.py

import mysql.connector
from flask import Blueprint, jsonify, request, current_app
from app import bcrypt
from datetime import timedelta
from db import get_db_connection
from flask_jwt_extended import (
    jwt_required, get_jwt_identity, get_jwt, verify_jwt_in_request, 
    unset_jwt_cookies, set_access_cookies, set_refresh_cookies, 
    create_access_token, create_refresh_token
)
from helpers import hash_password, verify_password
from routes.auth_routes import add_to_blocklist

user_bp = Blueprint('user_bp', __name__)

# GET ALL
@user_bp.route('/user', methods=['GET'])
def get_all_users():
  connection = get_db_connection()
  if connection: 
    try:
        cursor = connection.cursor()
        query = "SELECT * FROM users"
        cursor.execute(query)
        users = cursor.fetchall()
        if users:
            users_list = [
            {
                "id": user[0], 
                "email": user[1],
                "username": user[2], 
                "password": user[3],
                "bio": user[10],
                "confirmed": user[4],
                "confirmed_on": user[5],
                "membership": user[6],
                "projects": user[7],
                "projects_completed": user[8],
                "date_joined": user[9]
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
      # Close resources
      cursor.close()
      connection.close()
  # 500 Internal Server Error: Generic server-side failures
  return jsonify({"error": "Failed to connect to database"}), 500

# GET user
@user_bp.route('/user/info', methods=['GET'])
@jwt_required()
def get_user():
    username = get_jwt_identity()
    print(f"Fetching info for {username}...")
    connection = get_db_connection()
    if connection:
        cursor = connection.cursor()
        query = "SELECT * FROM users WHERE username = %s"
        try:
            cursor.execute(query, (username,))
            # Check that cursor did not return none
            user = cursor.fetchone()
            if user:
                user_data = {
                    "id": user[0], 
                    "email": user[1],
                    "username": user[2], 
                    "password": user[3],
                    "bio": user[10],
                    "confirmed": user[4],
                    "confirmed_on": user[5],
                    "membership": user[6],
                    "projects": user[7],
                    "projects_completed": user[8],
                    "date_joined": user[9]
                }
                # 200 OK: For a successful request that returns data
                return jsonify(user_data), 200
            else:
                # 404 Not Found: User not found
                return jsonify({"error": "User not found"}), 404
        except mysql.connector.Error as e:
            # 500 Internal Server Error: Generic server-side failures
            return jsonify({"error": str(e)}), 500
        finally:
            # Close resources
            cursor.close()
            connection.close()
    # 500 Internal Server Error: Generic server-side failures
    return jsonify({"error": "Failed to connect to database"}), 500

# UPDATE
# Updates username of a given user
@user_bp.route('/user/update-username', methods=['PUT'])
@jwt_required()
def update_username():
    current_username = get_jwt_identity()
    data = request.get_json()
    new_username = data['new_username']
    current_password = data['current_password']
    connection = get_db_connection()
    if connection:
        try:
            cursor = connection.cursor()
            # First, fetch current user and verify password
            query_a = "SELECT * FROM users WHERE username = %s"
            cursor.execute(query_a, (current_username,))
            user = cursor.fetchone()
            if user:
                # Retrieve stored password hash for user
                stored_hash = user[3]
                # print(f"stored hash: {stored_hash}")
                # Check that current password matches stored password
                if verify_password(current_password, stored_hash, bcrypt):
                    # Check if new username already exists in table
                    query_b = "SELECT * FROM users WHERE username = %s"
                    cursor.execute(query_b, (new_username,))
                    existing_user = cursor.fetchone()
                    if existing_user:
                        # 409 Conflict: Username already exists
                        return jsonify({"error": "Username already exists"}), 409
                            
                    # Structure query to update user record
                    query_c = "UPDATE users SET username = %s WHERE username = %s"
                    cursor.execute(query_c, (new_username, current_username,))
                    connection.commit()
                    
                    # Logic from logout()
                    try:
                        # Try to verify the access token without requiring it
                        verify_jwt_in_request(optional=True)
                        access_token = get_jwt()
                        if access_token:
                            jti_access = access_token["jti"]
                            add_to_blocklist(jti_access)
                    except Exception:
                        # Token might be expired, so skip blocklisting access token
                        pass  

                    try:
                        # Try to verify the refresh token manually if present
                        verify_jwt_in_request(optional=True, refresh=True)
                        refresh_token = get_jwt(refresh=True)
                        if refresh_token:
                            jti_refresh = refresh_token["jti"]
                            add_to_blocklist(jti_refresh)
                    except Exception:
                        # Token might be expired, so skip blocklisting refresh token
                        pass  
                    
                    response = jsonify({"message": "Logout successful"})
                    # Unset JWT cookies
                    unset_jwt_cookies(response) # <- look into this later. Why is the response encoded?
                    
                    new_access_token = create_access_token(identity=new_username, fresh=True)
                    new_refresh_token = create_refresh_token(identity=new_username)
                    response = jsonify({"message": "Username updated successfully; fresh tokens generated", "access_token": new_access_token})
                    # Store new tokens in cookies
                    set_access_cookies(response, new_access_token)
                    set_refresh_cookies(response, new_refresh_token)
                    
                    # 200 OK: For a successful request
                    return response, 200
                else:
                    # 401 Unauthorized: Current password is incorrect
                    return jsonify({"error": "Invalid current password"}), 401
            else:
                # 404 Not Found: User not found
                return jsonify({"error": "User not found"}), 404
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
# Updates password of a given user
@user_bp.route('/user/update-password', methods=['PUT'])
@jwt_required()
def update_password():
    username = get_jwt_identity()
    data = request.get_json()
    current_password = data['current_password']
    new_password = data['new_password']
    connection = get_db_connection()
    if connection:
        try:
            cursor = connection.cursor()
            # First, retrieve user by username (unique)
            query_a = "SELECT * FROM users WHERE username = %s"
            cursor.execute(query_a, (username,))
            user = cursor.fetchone()
            # Check if user is found
            if user:
                # Retrieve stored password hash for user
                stored_hash = user[3]
                # print(f"stored hash: {stored_hash}")
                # Check that current password matches stored password
                if verify_password(current_password, stored_hash, bcrypt):
                    # Hash new password
                    hashed_new_password = hash_password(new_password, bcrypt)
                    # Set new (hashed) password
                    query_b = "UPDATE users SET password = %s WHERE username = %s"
                    cursor.execute(query_b, (hashed_new_password, username,))
                    connection.commit()
                    # 200 OK: For a successful request
                    return jsonify({"message": "Password updated successfully"}), 200
                else:
                    # 401 Unauthorized: Current password is incorrect
                    return jsonify({"error": "Invalid current password"}), 401
            else:
                # 404 Not Found: User not found
                return jsonify({"error": "User not found"}), 404
        except mysql.connector.Error as e:
            # 500 Internal Server Error
            return jsonify({"error": f"Database error: {e}"}), 500
        finally:
            # Close resources
            cursor.close()
            connection.close()
    # 500 Internal Server Error: Generic server-side failures
    return jsonify({"error": "Failed to connect to database"}), 500

# CREATE and UPDATE endpoint for user bio
@user_bp.route('/user/set-bio', methods=['PUT'])
@jwt_required()
def set_bio():
    username = get_jwt_identity()
    data = request.get_json()
    bio = data['data']
    connection = get_db_connection()
    if connection:
        try:
            cursor = connection.cursor()
            query_a = "SELECT * FROM users WHERE username = %s"
            cursor.execute(query_a, (username,))
            user = cursor.fetchone()
            if not user:
                # 404 Not Found
                return jsonify({"error": f"User {username} not found"}), 404
            
            query_b = "UPDATE users SET bio = %s WHERE username = %s"
            cursor.execute(query_b, (bio, username))
            connection.commit()
            # 200 OK: For a successful request
            return jsonify({"message": "User bio updated successfully"}), 200
        except mysql.connector.Error as e:
            # 500 Internal Server Error
            return jsonify({"error": f"Database error: {e}"}), 500
        finally:
            # Close resources
            cursor.close()
            connection.close()
    # 500 Internal Server Error: Generic server-side failures
    return jsonify({"error": "Failed to connect to database"}), 500
    
# DELETE endpoint for user bio
@user_bp.route('/user/delete-bio', methods=['DELETE'])
@jwt_required()
def delete_bio():
    username = get_jwt_identity()
    connection = get_db_connection()
    if connection:
        try:
            cursor = connection.cursor()
            query_a = "SELECT * FROM users WHERE username = %s"
            cursor.execute(query_a, (username,))
            user = cursor.fetchone()
            if not user:
                # 404 Not Found
                return jsonify({"error": f"User {username} not found"}), 404
            
            query_b = "UPDATE users SET bio = NULL WHERE username = %s"
            cursor.execute(query_b, (username,))
            connection.commit()
            # 200 OK: For a successful request
            return jsonify({"message": "User bio updated successfully"}), 200
        except mysql.connector.Error as e:
            # 500 Internal Server Error
            return jsonify({"error": f"Database error: {e}"}), 500
        finally:
            # Close resources
            cursor.close()
            connection.close()
    # 500 Internal Server Error: Generic server-side failures
    return jsonify({"error": "Failed to connect to database"}), 500

# DELETE USER
# TODO: Test this function's project deletion with respect to collaborators
@user_bp.route('/user/delete', methods=['DELETE'])
@jwt_required()
def delete_user():
    username = get_jwt_identity()
    # Mimic logout. Get current access token's jti
    jti = get_jwt()['jti']
    current_app.blocklist.set(jti, "", ex=timedelta(minutes=30))
    connection = get_db_connection()
    try:
        # Try to verify the refresh token if present
        verify_jwt_in_request(optional=True, refresh=True)
        refresh_token = get_jwt(refresh=True)
        if refresh_token:
            jti_refresh = refresh_token["jti"]
            current_app.blocklist.set(jti_refresh, "", ex=timedelta(minutes=30))
    except Exception:
        # Token might be expired, so skip blocklisting refresh token
        pass 
    
    response = jsonify({"message": "User deleted successfully."})
    unset_jwt_cookies(response)
     
    if connection:
        try:
            cursor = connection.cursor()
            query_a = "SELECT * FROM users WHERE username = %s"
            cursor.execute(query_a, (username,))
            user = cursor.fetchone()
            if not user:
                # 404 Not Found: User not found
                return jsonify({"error": "User not found"}), 404
            user_project_count = user[7]
            if user_project_count != 0:
                query_b = "SELECT * FROM projects WHERE owner = %s"
                cursor.execute(query_b, (username,))
                projects = cursor.fetchall()
                # Check owned projects first
                for project in projects:
                    pid = project[0]
                    collaborator1 = project[2]
                    collaborator2 = project[3]
                    project_completed = project[8]
                    # Check collaborators on owned project
                    collaborators = []
                    if collaborator1:
                        collaborators.append(collaborator1)
                    if collaborator2:
                        collaborators.append(collaborator2)
                    for collaborator in collaborators:
                        # Decrement collaborator's projects count
                        query_c = "UPDATE users SET projects = projects - 1 WHERE username = %s"
                        cursor.execute(query_c, (collaborator,))
                        if project_completed:
                            # Decrement collaborator's project_completed count
                            query_d = "UPDATE users SET projects_completed = project_completed - 1 WHERE username = %s"
                            cursor.execute(query_d, (collaborator,)) 
                    # Delete tasks before project, as they are linked to project through pid 
                    query_e = "DELETE FROM tasks where pid = %s"
                    cursor.execute(query_e, (pid,))
                    # Delete project
                    query_f = "DELETE FROM projects WHERE id = %s"
                    cursor.execute(query_f, (pid,))
                # Next, check if the user has collabed on any projects
                if user_project_count > len(projects):
                    # Compile a list of projects where user is listed as a collaborator
                    collab_projects = []
                    query_g = "SELECT * FROM projects WHERE collaborator1 = %s"
                    cursor.execute(query_g, (username,))
                    collab_projects += cursor.fetchall()
                    query_h = "SELECT * FROM projects WHERE collaborator2 = %s"
                    cursor.execute(query_h, (username,))
                    collab_projects += cursor.fetchall()
                    # Remove user as collaborator
                    for collab_project in collab_projects:
                        pid = collab_project[0]
                        collaborator1 = collab_project[2]
                        collaborator2 = collab_project[3]
                        if collaborator1 == username:
                            query_i = "UPDATE projects SET collaborator1 = NULL WHERE id = %s"
                            cursor.execute(query_i, (pid,))
                        if collaborator2 == username:
                            query_j = "UPDATE projects SET collaborator2 = NULL WHERE id = %s"
                            cursor.execute(query_j, (username,))
            # Finally, delete user
            query_k = "DELETE FROM users WHERE username = %s"
            cursor.execute(query_k, (username,))
            # Commit changes
            connection.commit()
            # 200 OK: For a successful request
            return response, 200
        except mysql.connector.Error as e:
            connection.rollback()
            # 500 Internal Server Error
            return jsonify({"error": f"Database error: {e}"}), 500
        finally:
            # Close resources
            cursor.close()
            connection.close()
    # 500 Internal Server Error: Generic server-side failures
    return jsonify({"error": "Failed to connect to database"}), 500

