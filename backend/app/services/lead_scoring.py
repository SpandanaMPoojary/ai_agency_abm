import os
import psycopg2
from urllib.parse import urlparse

def get_db_connection():
    try:
        database_url = os.getenv('DATABASE_URL')
        if database_url:
            parsed = urlparse(database_url)
            conn = psycopg2.connect(
                host=parsed.hostname,
                port=parsed.port,
                database=parsed.path.lstrip('/'),
                user=parsed.username,
                password=parsed.password
            )
        else:
            conn = psycopg2.connect(
                host=os.getenv('DB_HOST', 'localhost'),
                port=os.getenv('DB_PORT', '5432'),
                database=os.getenv('DB_NAME', 'postgres'),
                user=os.getenv('DB_USER', 'postgres'),
                password=os.getenv('DB_PASSWORD', 'postgres')
            )
        return conn
    except Exception as e:
        print(f"Database error: {e}")
        return None

def update_lead_score(lead_id: int, activity_type: str):
    """
    Updates lead score or status based on activity.
    lead_id here refers to the account ID.
    """
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        with conn.cursor() as cursor:
            if activity_type == 'MESSAGE_SENT':
                print(f"Updating status to Active for lead {lead_id}")
                cursor.execute(
                    "UPDATE accounts SET status = 'Active' WHERE id = %s",
                    (lead_id,)
                )
            elif activity_type == 'LINK_CLICKED':
                print(f"Adding 20 points to lead {lead_id}")
                cursor.execute(
                    "UPDATE accounts SET lead_score = lead_score + 20 WHERE id = %s",
                    (lead_id,)
                )
            else:
                print(f"Unknown activity type: {activity_type}")
                return False
            
            conn.commit()
            return True
    except Exception as e:
        print(f"Error updating lead score: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()
