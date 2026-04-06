import os
import sys
from sqlmodel import Session, create_engine, select
from backend.main import Account, LeadScore

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:myp@ss123@localhost:5432/ai_agency_db")
engine = create_engine(DATABASE_URL)

def check_clicks():
    with Session(engine) as session:
        # Find all LeadScore entries for link clicks
        stmt = select(LeadScore).where(LeadScore.reason == "Follow-up Link Clicked")
        click_events = session.exec(stmt).all()
        
        if not click_events:
            print("No real prospects have clicked the tracking link yet.")
            return

        print(f"Found {len(click_events)} link click events in the database:")
        for event in click_events:
            account = session.get(Account, event.account_id)
            name = f"{account.first_name} {account.company_name}" if account else "Unknown Account"
            print(f"- Lead ID {event.account_id} ({name}) clicked at {event.timestamp}")

if __name__ == "__main__":
    check_clicks()
