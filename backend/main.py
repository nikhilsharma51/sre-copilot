import uuid
from dotenv import load_dotenv
load_dotenv()

from graph import build_incident_graph
from langgraph.checkpoint.sqlite import SqliteSaver

ALERT = "High error rate (>20%) on checkout-service for the last 15 minutes."
DB_PATH="incident.db"

def fresh_state(alert : str)-> dict:
    return {"messages": [], "alert": alert, "hypothesis": None, "proposal": None,
            "guardrail_result": None, "approved": None, "result": None,
            "actions_taken": [], "stop_reason": None, "timeline": []}

def main():
    thread_id = str(uuid.uuid4())[:8]
    with SqliteSaver.from_conn_string(DB_PATH) as saver:
        graph = build_incident_graph(checkpointer=saver)
        config = {"configurable":{"thread_id":thread_id}}
        result = graph.invoke(fresh_state(ALERT),config=config)

        print(f"\nthread_id: {thread_id}")
        for line in result["timeline"]:
            print("-", line)

        if "__interrupt__" in result:
            print("\n--- WAITING FOR APPROVAL ---")
            print(result["__interrupt__"][0].value)
            print(f"\nResume with:\n  python resume.py {thread_id} approve")
            print(f"  python resume.py {thread_id} deny \"reason here\"")
        else:
            print("\nFinished without needing approval (blocked by guardrails).")

if __name__ == "__main__":
    main()

# initial_state : TriageState = {
#         "messages": [],
#         "alert": ALERT,
#         "hypothesis": None,
#         "timeline": [],
# }
# def main():
#     graph = build_triage_graph()
#     result = graph.invoke({
#         "messages": [],
#         "alert": ALERT,
#         "hypothesis": None,
#         "timeline": [],
#     })

#     print("\n--- Hypothesis ---")
#     print(result["hypothesis"])
#     print("\n--- Timeline ---")
#     for line in result["timeline"]:
#         print("-", line)


# if __name__ == "__main__":
#     main()

