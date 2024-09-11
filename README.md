# Brainstorming app for computer science and technology students
Frontend can be found here: https://github.com/novoaj/brainstormai-frontend

## Description
This document specifies how our API works to perform CRUD operations with our MySQL database 
and interface with a Groq LLM API to generate project ideas catering to users' individual strengths 
and interests within programming. 

Technologies used: 
* Python
* Flask
* MySQL
* AWS RDS
* CORS
* JWT

## Setup Environment
Configure a virtual environment, activate it, and install the requirements.

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Running the app
```bash
(venv) % flask run
 * Serving Flask app 'main.py'
 * Debug mode: off
WARNING: This is a development server. Do not use it in a production deployment. Use a production WSGI server instead.
 * Running on http://127.0.0.1:5000
Press CTRL+C to quit
```