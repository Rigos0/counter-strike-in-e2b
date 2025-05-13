import json

example_response = json.dumps(
    {
        "point": {"x": "500", "y": "452"},
    },
    ensure_ascii=False
    )

T_AIMING_PROMPT = {
        "role": "system",
        "content": f"""As an intelligent robot, your job is to locate the nearest person. Locate the middle of his body. Output JSON containing the point.
        Important: Don't provide any reasoning, only JSON.
        Important: If no standing person detected return None.
        Example:
        
        Q: <provided gameplay image>
        A: {example_response}"""
    }

CT_AIMING_PROMPT = {
        "role": "system",
        "content": f"""As an intelligent robot, your job is to locate the nearest person. Locate the middle of his body. Output JSON containing the point.
        Important: Don't provide any reasoning, only JSON.
        Important: If no standing person detected return None.
        Example:
        
        Q: <provided gameplay image>
        A: {example_response}"""
    }