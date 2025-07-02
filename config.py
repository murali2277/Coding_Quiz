import os
import secrets
from pymongo import MongoClient

MONGO_URI = "mongodb+srv://ffsangam:FF%40sangam@cluster0.pbunrbm.mongodb.net/coding_quiz?retryWrites=true&w=majority&appName=Cluster0"
SECRET_KEY = os.environ.get("SECRET_KEY", "dev_default_secret")

print(secrets.token_hex(24))

client = MongoClient(MONGO_URI)
db = client["coding_quiz"]  # or your actual database name 
