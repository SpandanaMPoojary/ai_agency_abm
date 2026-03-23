from backend.app.db.setup_db import get_db_connection

def migrate():
    conn = get_db_connection()
    if not conn:
        print("Failed to connect to database.")
        return

    try:
        with conn.cursor() as cursor:
            # Add lead_score if missing
            cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name='accounts' AND column_name='lead_score';")
            if not cursor.fetchone():
                print("Adding lead_score column...")
                cursor.execute("ALTER TABLE accounts ADD COLUMN lead_score INTEGER DEFAULT 0;")
            
            # Add status if missing
            cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name='accounts' AND column_name='status';")
            if not cursor.fetchone():
                print("Adding status column...")
                cursor.execute("ALTER TABLE accounts ADD COLUMN status TEXT DEFAULT 'pending';")
                
            # Add email if missing (just in case)
            cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name='accounts' AND column_name='email';")
            if not cursor.fetchone():
                print("Adding email column...")
                cursor.execute("ALTER TABLE accounts ADD COLUMN email TEXT;")

            conn.commit()
            print("Migration completed successfully!")
    except Exception as e:
        print(f"Migration failed: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
