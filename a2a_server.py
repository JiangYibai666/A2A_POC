"""
Expose LangGraph agents as an A2A service so other agents can discover and call them.
"""

import json
from typing import Any
from flask import Flask, request, jsonify

from agents import invoice_agent, entity_agent

app = Flask(__name__)

AGENTS = {
    "invoice_agent": invoice_agent,
    "entity_agent": entity_agent,
}

AGENT_CARDS = {
    "invoice_agent": {
        "name": "invoice_agent",
        "description": "Query invoice information with filters by company and status",
        "version": "1.0.0",
        "capabilities": {"streaming": False},
        "skills": [
            {
                "id": "query-invoices",
                "name": "Query invoices",
                "description": "Query invoices for a specific company with optional status filtering"
            }
        ],
        "endpoints": {
            "tasks": "/a2a/invoice_agent/tasks"
        }
    },
    "entity_agent": {
        "name": "entity_agent",
        "description": "Query detailed company entity information",
        "version": "1.0.0",
        "capabilities": {"streaming": False},
        "skills": [
            {
                "id": "query-entity",
                "name": "Query company information",
                "description": "Get company registration data, address, industry, and related details"
            }
        ],
        "endpoints": {
            "tasks": "/a2a/entity_agent/tasks"
        }
    }
}


@app.route("/.well-known/agent.json")
def discover_all_agents():
    """
    A2A discovery endpoint that returns all available agents.
    This allows the orchestrator to discover agents dynamically.
    """
    return jsonify({
        "agents": [
            {
                "name": name,
                "url": f"http://localhost:5000/.well-known/{name}.json"
            }
            for name in AGENTS.keys()
        ]
    })


@app.route("/.well-known/<agent_name>.json")
def get_agent_card(agent_name: str):
    """Return the agent card for a specific agent."""
    if agent_name not in AGENT_CARDS:
        return jsonify({"error": "Agent not found"}), 404
    return jsonify(AGENT_CARDS[agent_name])


@app.route("/a2a/<agent_name>/tasks", methods=["POST"])
def handle_a2a_task(agent_name: str):
    """
    A2A task endpoint that accepts JSON-RPC requests.
    """
    if agent_name not in AGENTS:
        return jsonify({"jsonrpc": "2.0", "error": {"code": -32601, "message": "Agent not found"}}), 404
    
    data = request.get_json()
    task_id = data.get("params", {}).get("id")
    message = data.get("params", {}).get("message", {})
    user_query = message.get("parts", [{}])[0].get("text", "")
    
    # Invoke the LangGraph agent.
    agent = AGENTS[agent_name]
    config = {"configurable": {"thread_id": task_id or "default"}}
    
    result = agent.invoke(
        {"messages": [{"role": "user", "content": user_query}]},
        config=config
    )
    
    # Extract the agent's final reply.
    last_msg = result["messages"][-1]
    if isinstance(last_msg.content, list):
        final_message = " ".join(
            block.get("text", "")
            for block in last_msg.content
            if isinstance(block, dict) and block.get("type") == "text"
        )
    else:
        final_message = last_msg.content
    
    # Return the standard A2A response payload.
    return jsonify({
        "jsonrpc": "2.0",
        "id": data.get("id"),
        "result": {
            "id": task_id,
            "status": {"state": "completed"},
            "artifacts": [{
                "parts": [{"type": "text", "text": final_message}]
            }]
        }
    })


if __name__ == "__main__":
    print("A2A service started at http://localhost:5000")
    print("Agent card endpoint: http://localhost:5000/.well-known/agent.json")
    app.run(host="0.0.0.0", port=5000, debug=True)