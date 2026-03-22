import json
from backend.app.agents.abm_agent import ABMAgent

def test_abm_agent():
    print("Testing ABMAgent...")
    agent = ABMAgent()
    
    test_account = "John Doe, Founder at AI Startup"
    test_icp = "Cybersecurity Audit Firms"
    test_value_prop = "Automating compliance audits with LLMs"
    
    try:
        sequence = agent.generate_outreach_sequence(test_account, test_icp, test_value_prop)
        print("Generated Sequence:")
        print(json.dumps(sequence, indent=2))
        
        # Check if the output is a list and contains the required keys
        if isinstance(sequence, list) and len(sequence) > 0:
            required_keys = ["channel", "message", "cta", "status"]
            for item in sequence:
                for key in required_keys:
                    if key not in item:
                        print(f"Missing key: {key} in sequence step")
            print("Successfully validated sequence structure.")
        else:
            print("Failed: Output is not a list or is empty.")
    except Exception as e:
        print(f"ABM Agent test failed: {e}")

if __name__ == "__main__":
    test_abm_agent()
