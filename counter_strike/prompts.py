import json

example_response = json.dumps(
    {
        "point": {"x": "500", "y": "452"},
    },
    ensure_ascii=False
    )

T_ENEMY_DESCRIPTION = "<description> Does not wear a red headband and wears blue or grey clothing.</description>"
T_AIMING_PROMPT = {
        "role": "system",
        "content": f"""As an intelligent robot, your job is to locate the middle of the body of the nearest person which:{T_ENEMY_DESCRIPTION}". Locate the middle of his body. Output JSON containing the point.
        Important: Don't provide any reasoning, only JSON.
        Important: If the person doesn't match the description or no person found, return None.
        Example:
        
        Q: <provided gameplay image>
        A: {example_response}"""
    }

CT_ENEMY_DESCRIPTION = "<description> Has to wear a red helmet.</description>"
CT_AIMING_PROMPT = {
        "role": "system",
        "content": f"""As an intelligent robot, your job is to locate the middle of the body of the nearest person which: {CT_ENEMY_DESCRIPTION}. Output JSON containing the point.
        Important: Don't provide any reasoning, only JSON.
        Important: If the person doesn't match the description or no person found, return None.
        Example:
        
        Q: <provided gameplay image>
        A: {example_response}"""
    }