import os
import sys
from dotenv import load_dotenv

# Add the project root to sys.path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from backend.app.db.setup_db import get_db_connection

load_dotenv()

def seed_test_lead():
    print("--- Create Test Lead ---")
    name = input("Enter Lead Name (e.g. Spandana): ")
    default_email = os.getenv('TEST_EMAIL', '')
    email = input(f"Enter Lead Email [{default_email}]: ") or default_email
    
    if not email:
        print("Error: Email is required.")
        return
    
    conn = get_db_connection()
    if not conn:
        print("Failed to connect to database.")
        return

    try:
        with conn.cursor() as cursor:
            # Check if email column exists, if not add it (migration)
            cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name='accounts' AND column_name='email';")
            if not cursor.fetchone():
                print("Adding email column to accounts table...")
                cursor.execute("ALTER TABLE accounts ADD COLUMN email TEXT;")
            
            # Insert Test Lead
            cursor.execute(
                "INSERT INTO accounts (company_name, email, status) VALUES (%s, %s, %s) RETURNING id",
                ("Test Company", email, "pending")
            )
            account_id = cursor.fetchone()[0]
            
            cursor.execute(
                "INSERT INTO outreach_sequences (account_id, channel, message, cta, approval_status) VALUES (%s, %s, %s, %s, %s) RETURNING id",
                (account_id, "linkedin", f"Hello {name}, this is a test message.", "Test CTA", "draft")
            )
            outreach_id = cursor.fetchone()[0]
            
            conn.commit()
            print(f"Successfully inserted Test Lead for {name} ({email})")
            print(f"Account ID: {account_id}")
            print(f"Campaign (Outreach) ID: {outreach_id}")
            print(f"To test this safely, set TEST_EMAIL={email} in your .env file.")
    except Exception as e:
        print(f"Error seeding database: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    seed_test_lead()
