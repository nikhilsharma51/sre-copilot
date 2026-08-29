import uuid
import argparse
from dotenv import load_dotenv
import asyncio
load_dotenv()

from graph import build_incident_graph
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from report import render_report

ALERTS = {
    "checkout": "High error rate (>20%) on checkout-service for the last 15 minutes.",
    "disk": "payments-worker is failing to write job results; disk usage looks critical.",
}

DB_PATH="incident.db"

def parse_args():
    p = argparse.ArgumentParser(description="Start a new simulated incident.")
    p.add_argument("--scenario", choices=ALERTS.keys(), default="checkout")
    p.add_argument("--severity", choices=["P1", "P3"], default="P3")
    return p.parse_args()

def fresh_state(alert: str, severity: str) -> dict:
    return {"messages": [], "alert": alert, "severity": severity, "hypothesis": None,
            "proposal": None, "guardrail_result": None, "approved": None, "result": None,
            "actions_taken": [], "stop_reason": None, "timeline": []}


async def main():
    args = parse_args()
    thread_id = str(uuid.uuid4())[:8]
    async with AsyncSqliteSaver.from_conn_string(DB_PATH) as saver:
        graph = build_incident_graph(checkpointer=saver)
        config = {"configurable": {"thread_id": thread_id}}
        result = await graph.ainvoke(fresh_state(ALERTS[args.scenario],args.severity), config=config)

        interrupted = "__interrupt__" in result
        print(f"\nscenario: {args.scenario}   severity: {args.severity}   thread_id: {thread_id}")
        print(render_report(result, interrupted=interrupted))

        if interrupted:
            print(f"\nResume with:\n  python resume.py {thread_id} approve")
            print(f"  python resume.py {thread_id} deny \"reason here\"")

if __name__ == "__main__":
    asyncio.run(main())