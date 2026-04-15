from CLOUDSERVER.database.database import deploys_collection, payments_collection

# ==========================================
# 🤖 BOT DEPLOYMENT DB FUNCTIONS
# ==========================================

async def register_new_bot(bot_data: dict):
    """Naya bot DB mein register karega"""
    # ⚙️ NAYA: Default Auto-deploy ON set karega agar mention nahi hai
    if "auto_deploy" not in bot_data:
        bot_data["auto_deploy"] = True
        
    await deploys_collection.insert_one(bot_data)
    return True

async def get_bot_by_repo(repo_name: str):
    """GitHub repo name se bot ki details nikalega (Webhook ke liye)"""
    return await deploys_collection.find_one({"repo_name": repo_name})

async def check_pm2_name_in_db(pm2_name: str):
    """Check karega ki DB mein ye PM2 naam pehle se registered toh nahi hai"""
    bot = await deploys_collection.find_one({"pm2_name": pm2_name})
    return bool(bot)

async def get_bot_by_name(app_name: str):
    """PM2/App name se bot ki saari details (folder_path etc) nikalega"""
    return await deploys_collection.find_one({"pm2_name": app_name})

async def update_bot_repo_details(app_name: str, new_repo_url: str, new_start_cmd: str, new_repo_name: str):
    """User agar Repo URL ya Start Command change karta hai toh ye DB update karega"""
    result = await deploys_collection.update_one(
        {"pm2_name": app_name},
        {"$set": {
            "repo_url": new_repo_url,
            "repo_name": new_repo_name,
            "start_cmd": new_start_cmd
        }}
    )
    return result.modified_count > 0

async def update_bot_env_vars(app_name: str, env_data: dict):
    """MongoDB mein bhi env variables ka backup rakhenge taaki Frontend pe show ho sakein"""
    result = await deploys_collection.update_one(
        {"pm2_name": app_name},
        {"$set": {"env_vars": env_data}}
    )
    return result.modified_count > 0
    
async def delete_bot_from_db(app_name: str):
    """MongoDB se bot ka record hamesha ke liye delete kar dega"""
    result = await deploys_collection.delete_one({"pm2_name": app_name})
    return result.deleted_count > 0

# 🔥 NAYA: Auto-Deploy Toggle Function
async def toggle_auto_deploy(app_name: str, status: bool):
    """Auto-deploy (GitHub Webhook) ko ON/OFF karne ke liye"""
    result = await deploys_collection.update_one(
        {"pm2_name": app_name},
        {"$set": {"auto_deploy": status}}
    )
    return result.modified_count > 0

# ==========================================
# 💸 PAYMENT & TRANSACTION DB FUNCTIONS
# ==========================================

async def get_user_transaction_history(username: str):
    """User ki saari transactions fetch karega (Latest first)"""
    # -1 ka matlab hai descending order (Nayi payment sabse upar)
    cursor = payments_collection.find({"username": username}).sort("timestamp", -1)
    transactions = await cursor.to_list(length=100) # Max 100 history dikhayenge
    
    # MongoDB ke ObjectID ko string mein convert karna zaroori hai JSON ke liye
    history = []
    for txn in transactions:
        txn["_id"] = str(txn["_id"])
        history.append(txn)
        
    return history
    
