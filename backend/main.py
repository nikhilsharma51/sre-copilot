from dotenv import load_dotenv
load_dotenv()

from alerts.agents.triage import build_triage_graph,TriageState

ALERT = "High error rate (>20%) on checkout-service for the last 15 minutes."

initial_state : TriageState = {
        "messages": [],
        "alert": ALERT,
        "hypothesis": None,
        "timeline": [],
}
def main():
    graph = build_triage_graph()
    result = graph.invoke({
        "messages": [],
        "alert": ALERT,
        "hypothesis": None,
        "timeline": [],
    })

    print("\n--- Hypothesis ---")
    print(result["hypothesis"])
    print("\n--- Timeline ---")
    for line in result["timeline"]:
        print("-", line)


if __name__ == "__main__":
    main()

