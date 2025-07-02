from flask import current_app
from pymongo import MongoClient

def get_user_collection():
    client = MongoClient(current_app.config['MONGO_URI'])
    db = client["coding_quiz"]
    return db.quiz

def find_user_by_email(email):
    users = get_user_collection()
    return users.find_one({"email": email})

def find_user_by_rollno(rollno):
    users = get_user_collection()
    return users.find_one({"rollno": rollno})

def update_user_password_and_first_login(rollno, new_password_hash):
    users = get_user_collection()
    users.update_one({"rollno": rollno}, {"$set": {"password": new_password_hash, "first_login": False}}) 