# helpers.py

# PROMPT helper: parse inputs lists to engineer prompt
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

# PROMPT helper: conjoin list of things using commas and/or 'and'
def conjunct_me(list):
  if len(list) > 2:
    joined_string = ", ".join(list[:-1]) + ", and " + list[-1]
    return joined_string
  elif len(list) == 2:
    joined_string = " and ".join(list)
    return joined_string
  else:
    return list[0]