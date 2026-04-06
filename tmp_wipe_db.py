import os
from sqlmodel import Session, create_engine, select
from backend.main import Account, OutreachSequence, LeadScore

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:myp@ss123@localhost:5432/ai_agency_db")
engine = create_engine(DATABASE_URL)

def wipe_db():
    with Session(engine) as session:
        # Delete LeadScores
        scores = session.exec(select(LeadScore)).all()
        for s in scores: session.delete(s)
            
        # Delete OutreachSequences
        seqs = session.exec(select(OutreachSequence)).all()
        for s in seqs: session.delete(s)
            
        # Delete Accounts
        accs = session.exec(select(Account)).all()
        for a in accs: session.delete(a)
            
        session.commit()
        print("Database wiped completely.")

if __name__ == "__main__":
    wipe_db()
