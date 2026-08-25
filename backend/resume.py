# resume.py
import sys
import asyncio
from dotenv import load_dotenv
load_dotenv()

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.types import Command
from graph import build_incident_graph
from report import render_report

DB_PATH = "incident.db"

async def main():
    if len(sys.argv) < 3:
        print("usage: python resume.py <thread_id> <approve|deny> [reason]")
        sys.exit(1)
    thread_id, decision = sys.argv[1], sys.argv[2]
    reason = sys.argv[3] if len(sys.argv) > 3 else None

    async with AsyncSqliteSaver.from_conn_string(DB_PATH) as saver:
        graph = build_incident_graph(checkpointer=saver)
        config = {"configurable": {"thread_id": thread_id}}
        result = graph.invoke(
            Command(resume={"approved": decision == "approve", "reason": reason}),
            config=config,
        )
        print(render_report(result))

if __name__ == "__main__":
    asyncio.run(main())