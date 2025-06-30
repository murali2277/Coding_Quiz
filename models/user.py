from flask import current_app
from pymongo import MongoClient

def get_user_collection():
    client = MongoClient(current_app.config['MONGO_URI'])
    db = client.get_database()
    return db.users

def find_user_by_email(email):
    users = get_user_collection()
    return users.find_one({"email": email}) 