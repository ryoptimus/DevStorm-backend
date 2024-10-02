# user_routes.py

import mysql.connector
from flask import Blueprint, jsonify, request
from app import bcrypt
from db import get_db_connection
from flask_jwt_extended import jwt_required, get_jwt_identity
from helpers import hash_password, verify_password

user_bp = Blueprint('user_bp', __name__)

# GET ALL
@user_bp.route('/user', methods=['GET'])
def get_all_users():
  connection = get_db_connection()
  if connection:
    cursor = connection.cursor()
    query = "SELECT * FROM users"
    try:
      cursor.execute(query)
      users = cursor.fetchall()
      if users:
        users_list = [
          {
            "id": user[0], 
            "email": user[1],
            "username": user[2], 
            "password": user[3],
            "membership": user[4],
            "projects": user[5],
            "projects_completed": user[6],
            "date_joined": user[7]
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
                    "membership": user[4],
                    "projects": user[5],
                    "projects_completed": user[6],
                    "date_joined": user[7]
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

# UPDATE
# Updates password of a given user
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
                    # 200 OK: For a successful request
                    return jsonify({"message": "Username updated successfully"}), 200
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

# DELETE
@user_bp.route('/user/delete', methods=['DELETE'])
@jwt_required()
def delete_record():
    username = get_jwt_identity()
    connection = get_db_connection()
    if connection:
        try:
            cursor = connection.cursor()
            query = "DELETE FROM users WHERE username = %s"
            cursor.execute(query, (username,))
            # Commit changes
            connection.commit()
            # 200 OK: For a successful request
            return jsonify({"message": "User deleted successfully."}), 200
        except mysql.connector.Error as e:
            # 500 Internal Server Error
            return jsonify({"error": f"Database error: {e}"}), 500
        finally:
            # Close resources
            cursor.close()
            connection.close()
    # 500 Internal Server Error: Generic server-side failures
    return jsonify({"error": "Failed to connect to database"}), 500

