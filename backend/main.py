import uuid
from dotenv import load_dotenv
import asyncio
load_dotenv()

from graph import build_incident_graph
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from report import render_report

ALERT = "High error rate (>20%) on checkout-service for the last 15 minutes."
DB_PATH="incident.db"

def fresh_state(alert : str)-> dict:
    return {"messages": [], "alert": alert, "hypothesis": None, "proposal": None,
            "guardrail_result": None, "approved": None, "result": None,
            "actions_taken": [], "stop_reason": None, "timeline": []}

async def main():
    thread_id = str(uuid.uuid4())[:8]
    async with AsyncSqliteSaver.from_conn_string(DB_PATH) as saver:
        graph = build_incident_graph(checkpointer=saver)
        config = {"configurable": {"thread_id": thread_id}}
        result = graph.invoke(fresh_state(ALERT), config=config)

        interrupted = "__interrupt__" in result
        print(f"\nthread_id: {thread_id}")
        print(render_report(result, interrupted=interrupted))

        if interrupted:
            print(f"\nResume with:\n  python resume.py {thread_id} approve")
            print(f"  python resume.py {thread_id} deny \"reason here\"")

if __name__ == "__main__":
    asyncio.run(main())