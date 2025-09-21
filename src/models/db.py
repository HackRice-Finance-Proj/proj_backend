import os
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.database import Database
from pymongo.collection import Collection
from fastapi import HTTPException

load_dotenv()

class DatabaseConfig:
    """Database configuration and connection management"""
    
    def __init__(self):
        self.client: MongoClient = None
        self.db: Database = None
        self.users: Collection = None
        
    def initialize_mongodb(self) -> None:
        """Initialize MongoDB connection"""
        try:
            mongo_uri = os.getenv("MONGODB_URI")
            if not mongo_uri:
                raise ValueError("MONGODB_URI not found in environment variables")
            
            self.client = MongoClient(mongo_uri)
            self.db = self.client.get_database("credit_card_db")
            self.users = self.db.get_collection("users")
            
            # Test the connection
            self.client.admin.command('ping')
            print("✅ MongoDB connection successful")
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to connect to MongoDB: {e}")
    
    def close_connections(self) -> None:
        """Close database connections"""
        if self.client is not None:  # Fix: Use 'is not None'
            self.client.close()
            print("✅ MongoDB connection closed")

    def get_users_collection(self) -> Collection:
        """Get the users collection"""
        if self.users is None:  # Fix: Use 'is None' instead of 'not self.users'
            raise HTTPException(status_code=500, detail="Database not initialized")
        return self.users
    
    def get_database(self) -> Database:
        """Get the database instance"""
        if self.db is None:  # Fix: Use 'is None' instead of 'not self.db'
            raise HTTPException(status_code=500, detail="Database not initialized")
        return self.db