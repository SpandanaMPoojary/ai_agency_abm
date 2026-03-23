from backend.app.db.setup_db import get_db_connection

def migrate_v3():
    conn = get_db_connection()
    if not conn:
        return

    try:
        with conn.cursor() as cursor:
            # Add human_notes to accounts
            cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name='accounts' AND column_name='human_notes';")
            if not cursor.fetchone():
                print("Adding human_notes column to accounts...")
                cursor.execute("ALTER TABLE accounts ADD COLUMN human_notes TEXT;")

            conn.commit()
            print("Step 3 Migration completed successfully!")
    except Exception as e:
        print(f"Migration failed: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_v3()
