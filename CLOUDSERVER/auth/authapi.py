import httpx

async def verify_turnstile(token: str):
    secret = os.getenv("CLOUDFLARE_SECRET_KEY")
    url = "https://challenges.cloudflare.com/turnstile/v0/siteverify"
    
    async with httpx.AsyncClient() as client:
        response = await client.post(url, data={
            "secret": secret,
            "response": token
        })
        res = response.json()
        return res.get("success", False)
      
