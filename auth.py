def login(username, password):
    if not username or not password:
        raise ValueError("Username and password required")
    return {"status": "success", "user": username}

def logout(user_id):
    return {"status": "logged_out", "user_id": user_id}

def validate_token(token):
    if not token:
        return False
    return True