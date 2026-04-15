from fastapi import Security, HTTPException
from fastapi.security import APIKeyHeader
from CLOUDSERVER.database.user import get_user_by_api_key  # 🚀 MongoDB wala import

# Header mein 'x-api-key' naam se password aayega
api_key_header = APIKeyHeader(name="x-api-key", auto_error=False)

async def verify_api_key(api_key: str = Security(api_key_header)):
    """
    Ye function har secure API hit (deploy, restart) se pehle chalega.
    Check karega ki API key hamare MongoDB database mein exist karti hai ya nahi.
    """
    if not api_key:
        raise HTTPException(status_code=403, detail="🚨 Access Denied: API Key is missing in headers!")

    # 🔍 MongoDB mein search maro API key ke zariye
    user = await get_user_by_api_key(api_key)

    if not user:
        # Agar key match nahi hui database mein
        raise HTTPException(status_code=403, detail="🚨 Access Denied: Invalid API Key! Token MongoDB mein nahi mila.")
        
    # 🔥 Key valid hai, user ka naam return kar do (taaki deploy payload owner set kar sake)
    # user.get("username") use kar rahe hain kyunki MongoDB humein dictionary return karta hai
    return user.get("username", "Unknown_Owner")
    
