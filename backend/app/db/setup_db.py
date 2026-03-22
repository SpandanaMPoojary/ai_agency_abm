import os
import psycopg2
from psycopg2 import sql
from urllib.parse import urlparse

# Try to load dotenv if available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # Use os.environ directly

def get_db_connection():
    """Establish database connection"""
    try:
        database_url = os.getenv('DATABASE_URL')
        if database_url:
            # Parse DATABASE_URL
            parsed = urlparse(database_url)
            conn = psycopg2.connect(
                host=parsed.hostname,
                port=parsed.port,
                database=parsed.path.lstrip('/'),
                user=parsed.username,
                password=parsed.password
            )
        else:
            # Fallback to individual variables
            conn = psycopg2.connect(
                host=os.getenv('DB_HOST', 'localhost'),
                port=os.getenv('DB_PORT', '5432'),
                database=os.getenv('DB_NAME', 'postgres'),
                user=os.getenv('DB_USER', 'postgres'),
                password=os.getenv('DB_PASSWORD', 'postgres')
            )
        return conn
    except Exception as e:
        print(f"Error connecting to database: {e}")
        return None

def create_tables():
    """Create the accounts and outreach_sequences tables"""
    conn = get_db_connection()
    if not conn:
        return False

    try:
        with conn.cursor() as cursor:
            # Create accounts table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS accounts (
                    id SERIAL PRIMARY KEY,
                    company_name TEXT NOT NULL,
                    industry TEXT,
                    website TEXT,
                    icp_score INTEGER,
                    lead_score INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'pending'
                );
            """)

            # Create outreach_sequences table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS outreach_sequences (
                    id SERIAL PRIMARY KEY,
                    account_id INTEGER REFERENCES accounts(id),
                    channel TEXT,
                    message TEXT,
                    cta TEXT,
                    approval_status TEXT DEFAULT 'draft'
                );
            """)

            # Commit the changes
            conn.commit()
            print("Tables created successfully!")
            return True

    except Exception as e:
        print(f"Error creating tables: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    success = create_tables()
    if success:
        print("Database setup completed successfully.")
    else:
        print("Failed to set up database.")