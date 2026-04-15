from fastapi import Security, HTTPException
from fastapi.security import APIKeyHeader
import json
import os

# Header mein 'x-api-key' naam se password aayega
api_key_header = APIKeyHeader(name="x-api-key", auto_error=False)

USERS_DB_FILE = "users_db.json"

def verify_api_key(api_key: str = Security(api_key_header)):
    """
    Ye function har secure API hit (deploy, restart) se pehle chalega.
    Check karega ki API key hamare database mein exist karti hai ya nahi.
    """
    if not api_key:
        raise HTTPException(status_code=403, detail="🚨 Access Denied: API Key is missing in headers!")

    if not os.path.exists(USERS_DB_FILE):
        raise HTTPException(status_code=500, detail="🚨 Server Error: Users database not found!")

    try:
        with open(USERS_DB_FILE, "r") as f:
            users = json.load(f)

        # Check if the provided API key matches any user in the DB
        for username, user_data in users.items():
            if user_data.get("api_key") == api_key:
                return username  # Key valid hai, user ka naam return kar do

        # Agar loop khatam ho gaya aur key nahi mili:
        raise HTTPException(status_code=403, detail="🚨 Access Denied: Invalid API Key!")
        
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="🚨 Server Error: Database corrupted!")

