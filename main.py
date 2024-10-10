# main.py

from app import create_app
from db import create_users_table, create_projects_table, create_tasks_table, drop_tables

app, jwt, bcrypt = create_app()

# Import blueprints from the routes module
from routes.auth_routes import auth_bp
from routes.user_routes import user_bp
from routes.ai_routes import ai_bp
from routes.project_routes import project_bp
from routes.task_routes import task_bp

# Register the blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(user_bp)
app.register_blueprint(ai_bp)
app.register_blueprint(project_bp)
app.register_blueprint(task_bp)

# print(app.url_map)

# drop_tables()
create_users_table()
create_projects_table()
create_tasks_table()
  
if __name__ == "__main__":
  app.run(debug=True)
