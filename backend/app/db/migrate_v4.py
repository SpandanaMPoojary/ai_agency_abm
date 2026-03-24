import os
import psycopg2
from urllib.parse import urlparse
from dotenv import load_dotenv

load_dotenv()

def migrate():
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("DATABASE_URL not set")
        return

    parsed = urlparse(database_url)
    conn = psycopg2.connect(
        host=parsed.hostname,
        port=parsed.port,
        database=parsed.path.lstrip('/'),
        user=parsed.username,
        password=parsed.password
    )

    try:
        with conn.cursor() as cursor:
            # Create lead_scores table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS lead_scores (
                    id SERIAL PRIMARY KEY,
                    account_id INTEGER REFERENCES accounts(id),
                    score INTEGER DEFAULT 0,
                    reason TEXT DEFAULT 'Initial approval',
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            conn.commit()
            print("lead_scores table created successfully!")
    except Exception as e:
        print(f"Migration failed: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
