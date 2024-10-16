from pymongo import MongoClient
from werkzeug.security import generate_password_hash

from user import User

client = MongoClient("mongodb+srv://test:test@chatweb.1niledn.mongodb.net/")

chat_db = client.get_database("chatDB")
users_collection = chat_db.get_collection("users")



def save_user(username, email, password):
    password_hash = generate_password_hash(password)
        
        # 
    
    
    users_collection.insert_one({'username': username, 'email': email, 'password': password_hash})
    
"""save_user("kshitij","singhkshitij.com","kshitij")"""
    
    

def get_user(username):
    user_data = users_collection.find_one({'username': username})
    return User(user_data['username'], user_data['email'], user_data['password']) if user_data else None