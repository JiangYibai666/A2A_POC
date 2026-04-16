# main.py
"""
Run sample flows for the full multi-agent system.
"""

from supervisor_app import app as supervisor_app
from a2a_orchestrator import create_orchestrator_graph


def get_message_text(msg) -> str:
    """Extract plain text from a message, handling structured content blocks."""
    if isinstance(msg.content, str):
        return msg.content
    if isinstance(msg.content, list):
        return " ".join(
            block.get("text", "")
            for block in msg.content
            if isinstance(block, dict) and block.get("type") == "text"
        )
    return str(msg.content)


def test_supervisor():
    """Test supervisor mode with direct invocation."""
    print("=" * 50)
    print("[TEST] Test 1: Supervisor multi-agent mode")
    print("=" * 50)
    
    config = {"configurable": {"thread_id": "test-001"}}
    
    # Test invoice lookup.
    result = supervisor_app.invoke(
        {"messages": [{"role": "user", "content": "Query pending invoices for company comp-001"}]},
        config=config
    )
    print(f"User: Query pending invoices for company comp-001")
    print(f"Assistant: {get_message_text(result['messages'][-1])}\n")
    
    # Test entity lookup.
    result = supervisor_app.invoke(
        {"messages": [{"role": "user", "content": "Tell me the company information for comp-002"}]},
        config=config
    )
    print(f"User: Tell me the company information for comp-002")
    print(f"Assistant: {get_message_text(result['messages'][-1])}\n")


def test_a2a_orchestrator():
    """Test A2A orchestrator mode after starting the A2A service."""
    print("=" * 50)
    print("[TEST] Test 2: A2A orchestrator mode")
    print("=" * 50)
    print("[WARNING] Please run: python a2a_server.py")
    
    graph = create_orchestrator_graph()
    config = {"configurable": {"thread_id": "a2a-001"}}
    
    # Test invoice lookup.
    result = graph.invoke(
        {"messages": [{"role": "user", "content": "Which overdue invoices does comp-001 have?"}]},
        config=config
    )
    print(f"User: Which overdue invoices does comp-001 have?")
    print(f"Assistant: {get_message_text(result['messages'][-1])}\n")
    
    # Test entity lookup.
    result = graph.invoke(
        {"messages": [{"role": "user", "content": "Registration information for Doxa Holdings Singapore"}]},
        config=config
    )
    print(f"User: Registration information for Doxa Holdings Singapore")
    print(f"Assistant: {get_message_text(result['messages'][-1])}\n")


if __name__ == "__main__":
    test_supervisor()
    test_a2a_orchestrator()