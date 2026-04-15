from CLOUDSERVER.database.database import deploys_collection

async def register_new_bot(bot_data: dict):
    """Naya bot DB mein register karega"""
    await deploys_collection.insert_one(bot_data)
    return True

async def get_bot_by_repo(repo_name: str):
    """GitHub repo name se bot ki details nikalega (Webhook ke liye)"""
    return await deploys_collection.find_one({"repo_name": repo_name})

async def check_pm2_name_in_db(pm2_name: str):
    """Check karega ki DB mein ye PM2 naam pehle se registered toh nahi hai"""
    bot = await deploys_collection.find_one({"pm2_name": pm2_name})
    return bool(bot)

# 🔥 NAYA FUNCTION ADD KIYA HAI (Dashboard Actions ke liye)
async def get_bot_by_name(app_name: str):
    """PM2/App name se bot ki saari details (folder_path etc) nikalega"""
    return await deploys_collection.find_one({"pm2_name": app_name})
    
