import os
import sys
from sqlmodel import Session, create_engine, select
from backend.main import Account, LeadScore

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:myp@ss123@localhost:5432/ai_agency_db")
engine = create_engine(DATABASE_URL)

def check_scores():
    with Session(engine) as session:
        accounts = session.exec(select(Account)).all()
        if not accounts:
            print("No accounts in the database.")
            return None
        
        target = accounts[-1] # Get latest lead
        print(f"--- Lead: {target.first_name} {target.company_name} (ID: {target.id}) ---")
        print(f"Current Formatted Score: {target.lead_score}")
        print(f"Current Status: {target.status}")
        
        # Check specific score entries
        scores = session.exec(select(LeadScore).where(LeadScore.account_id == target.id)).all()
        print("Score History in DB:")
        for s in scores:
            print(f" - +{s.score} pts for '{s.reason}' at {s.timestamp}")
            
        return target.id

if __name__ == "__main__":
    check_scores()
