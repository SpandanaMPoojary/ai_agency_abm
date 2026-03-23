from backend.app.db.setup_db import get_db_connection

def migrate_v2():
    conn = get_db_connection()
    if not conn:
        return

    try:
        with conn.cursor() as cursor:
            cols_to_add = [
                ("step_1_linkedin", "TEXT"),
                ("step_2_email", "TEXT"),
                ("step_3_followup", "TEXT")
            ]
            
            for col_name, col_type in cols_to_add:
                cursor.execute(f"SELECT column_name FROM information_schema.columns WHERE table_name='outreach_sequences' AND column_name='{col_name}';")
                if not cursor.fetchone():
                    print(f"Adding {col_name} column...")
                    cursor.execute(f"ALTER TABLE outreach_sequences ADD COLUMN {col_name} {col_type};")

            conn.commit()
            print("Step 2 Migration completed successfully!")
    except Exception as e:
        print(f"Migration failed: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_v2()
