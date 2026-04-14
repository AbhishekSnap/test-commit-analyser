from auth import login, logout, validate_token

def test_login():
    result = login("abhishek", "password123")
    assert result["status"] == "success"

def test_logout():
    result = logout("123")
    assert result["status"] == "logged_out"

def test_validate_token():
    assert validate_token("abc123") == True
    assert validate_token("") == False