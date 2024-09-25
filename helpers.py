# helpers.py

from pydantic import BaseModel
from typing import List

# PROMPT_AI helper: data model for project idea generation
class ProjectIdea(BaseModel):
    project_title: str
    description: str
    steps: List[str]

# PROMPT_AI helper: parse inputs lists to engineer prompt
# Prompt example:
#   I am a role[0] and role[1] using technology[0] and technology[1] 
#   and technology[2] in the industries[0] industry. Generate a project idea.
def engineer_prompt(roles, technologies, industries) -> str:
  if len(industries) > 1:
    prompt = (
      "I am a " + conjunct_me([role.lower() for role in roles]) +
      " using " + conjunct_me(technologies) +
      " in the " + conjunct_me([industry.lower() for industry in industries]) +
      " industries. Generate a project idea."
    )
  else:
    prompt = (
      "I am a " + conjunct_me([role.lower() for role in roles]) +
      " using " + conjunct_me(technologies) +
      " in the " + conjunct_me([industry.lower() for industry in industries]) +
      " industry. Generate a project idea."
      )
  return prompt

# PROMPT_AI helper: conjoin list of things using commas and/or 'and'
def conjunct_me(list):
  if len(list) > 2:
    joined_string = ", ".join(list[:-1]) + ", and " + list[-1]
    return joined_string
  elif len(list) == 2:
    joined_string = " and ".join(list)
    return joined_string
  else:
    return list[0]

# LOGIN and REGISTER helpers: hash and verify passwords using bcrypt
def hash_password(password: str, bcrypt):
    # Utilize bcrypt with an automatically generated salt
    return bcrypt.generate_password_hash(password)
  
def verify_password(plain_password, hashed_password, bcrypt) -> bool:
    # Verify the hashed password
    return bcrypt.check_password_hash(hashed_password, plain_password)