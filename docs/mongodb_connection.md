
from pymongo import MongoClient
from pymongo.server_api import ServerApi

uri = "mongodb+srv://radarcuan_db:<db_password>@radarcuan.h9xxnv0.mongodb.net/?appName=RadarCuan"

# Create a new client and connect to the server
client = MongoClient(uri, server_api=ServerApi('1'))

# Send a ping to confirm a successful connection
try:
    client.admin.command('ping')
    print("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
    print(e)