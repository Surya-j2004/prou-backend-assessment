import os
import psycopg2
from psycopg2.extras import RealDictCursor
import time


DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://surya@localhost/prou_db")


if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

def get_db_connection():
    while True:
        try:
            
            conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
            return conn
        except Exception as e:
            print("Connecting to database failed. Retrying in 2s...")
            print(f"Error: {e}")
            time.sleep(2)

def init_db():
    """Create tables if they don't exist (Raw SQL)"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 1. Create Employees Table (Now with password_hash)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS employees (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                email VARCHAR(100) UNIQUE NOT NULL,
                role VARCHAR(50) NOT NULL,
                password_hash VARCHAR(200) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # 2. Create Tasks Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id SERIAL PRIMARY KEY,
                title VARCHAR(200) NOT NULL,
                description TEXT,
                is_completed BOOLEAN DEFAULT FALSE,
                owner_id INTEGER REFERENCES employees(id) ON DELETE CASCADE
            );
        """)
        
        conn.commit()
        print("Database tables initialized successfully.")
    except Exception as e:
        print(f"Error initializing DB: {e}")
    finally:
        # Ensures these are always closed, even if an error occurs
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()