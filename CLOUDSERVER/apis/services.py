from fastapi import APIRouter, Depends, HTTPException
from CLOUDSERVER.auth.verify import verify_api_key
from CLOUDSERVER.database.database import deploys_collection

router = APIRouter()

@router.get("/services")
async def get_my_services(username: str = Depends(verify_api_key)):
    """
    Ye API token check karegi aur us specific user ke saare bots MongoDB se nikaal kar degi.
    """
    try:
        # MongoDB Query: Sirf wahi bots nikaal jinka "owner" ye user hai
        cursor = deploys_collection.find({"owner": username})
        bots = await cursor.to_list(length=100) # Ek baar mein max 100 bots fetch karega
        
        # MongoDB ka `_id` raw format mein JSON read nahi kar pata, isko string karna padta hai
        for bot in bots:
            bot["_id"] = str(bot["_id"])

        return {
            "status": "success",
            "user": username,
            "total_services": len(bots),
            "services": bots,
            "message": "🔥 Data fetched successfully for your dashboard!"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database Error: {str(e)}")
      
