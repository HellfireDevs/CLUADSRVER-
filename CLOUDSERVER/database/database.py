from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")

if not MONGO_URI:
    print("🚨 [DB ERROR] MongoDB URI not found in .env file!")

# Async MongoDB Connection
client = AsyncIOMotorClient(MONGO_URI)

# Database ka naam
db = client["CloudEngineDB"]

# ==========================================
# 📦 COLLECTIONS (Tables)
# ==========================================
users_collection = db["users"]
deploys_collection = db["deploys"]

# 🔥 Naya Collection Support Tickets ke liye
tickets_collection = db["tickets"] 

print("✅ [DB] MongoDB Database connection initialized and collections mapped!")
