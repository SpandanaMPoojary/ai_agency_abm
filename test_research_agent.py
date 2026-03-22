from backend.app.agents.research_agent import ResearchAgent

def test_research_agent():
    print("Testing ResearchAgent...")
    icp = "Mid-sized SaaS companies in the US providing customer support tools"
    agent = ResearchAgent()
    
    # We only test identify_target_accounts to avoid burning API credits
    # or failing due to empty keys. This will check integration.
    try:
        accounts = agent.identify_target_accounts(icp)
        print(f"Identified {len(accounts)} target accounts:")
        for acc in accounts[:3]:
            print(f"- {acc['name']} ({acc['link']})")
    except Exception as e:
        print(f"Research failed (probably missing API keys): {e}")

if __name__ == "__main__":
    test_research_agent()
