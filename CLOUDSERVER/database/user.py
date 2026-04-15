from CLOUDSERVER.database.database import users_collection

async def create_user(user_data: dict):
    """Naya user DB mein save karega"""
    await users_collection.insert_one(user_data)
    return True

async def get_user_by_username(username: str):
    """Username se user dhoondega"""
    return await users_collection.find_one({"username": username})

async def get_user_by_email(email: str):
    """Email se user dhoondega"""
    return await users_collection.find_one({"email": email})

async def get_user_by_api_key(api_key: str):
    """API Key se verify karega (Security ke liye)"""
    return await users_collection.find_one({"api_key": api_key})
  
