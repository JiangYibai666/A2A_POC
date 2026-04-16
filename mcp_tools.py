"""
Mock MCP tool calls. In a real deployment these would call actual API services.
"""

from typing import Optional
from langchain_core.tools import tool


@tool
def query_invoices(company_uuid: str, status: Optional[str] = None) -> str:
    """
    Query invoice information for a specific company.
    Args:
        company_uuid: Unique company identifier
        status: Optional invoice status filter (PENDING, PAID, OVERDUE)
    """
    # Mock data. In production this would call the internal invoice API.
    mock_invoices = {
        "comp-001": [
            {"id": "INV-2026-001", "amount": 12500.00, "status": "PENDING", "vendor": "Acme Corp"},
            {"id": "INV-2026-002", "amount": 8900.50, "status": "PAID", "vendor": "Global Supplies"},
            {"id": "INV-2026-003", "amount": 3400.00, "status": "OVERDUE", "vendor": "Tech Solutions"},
        ],
        "comp-002": [
            {"id": "INV-2026-004", "amount": 6700.00, "status": "PENDING", "vendor": "Office World"},
            {"id": "INV-2026-005", "amount": 12300.00, "status": "PENDING", "vendor": "IT Services Ltd"},
        ]
    }
    
    invoices = mock_invoices.get(company_uuid, [])
    if status:
        invoices = [inv for inv in invoices if inv["status"] == status]
    
    if not invoices:
        return f"No invoice records found for company {company_uuid}."
    
    result = f"Invoice list for company {company_uuid}:\n"
    for inv in invoices:
        result += f"  - {inv['id']}: ${inv['amount']:.2f} ({inv['status']}) - Vendor: {inv['vendor']}\n"
    return result


@tool
def query_entity(company_uuid: str) -> str:
    """
    Query detailed information for a company entity.
    Args:
        company_uuid: Unique company identifier
    """
    mock_entities = {
        "comp-001": {
            "name": "Doxa Holdings Singapore",
            "registration_no": "202012345A",
            "address": "1 Raffles Place, Singapore 048616",
            "industry": "Financial Services",
            "employee_count": 150
        },
        "comp-002": {
            "name": "Doxa Technologies Malaysia",
            "registration_no": "LL12345",
            "address": "Level 20, Menara KL, Kuala Lumpur",
            "industry": "Technology",
            "employee_count": 85
        }
    }
    
    entity = mock_entities.get(company_uuid)
    if not entity:
        return f"No company information found for {company_uuid}."
    
    return (
        f"Company information:\n"
        f"  Name: {entity['name']}\n"
        f"  Registration No: {entity['registration_no']}\n"
        f"  Address: {entity['address']}\n"
        f"  Industry: {entity['industry']}\n"
        f"  Employee Count: {entity['employee_count']}"
    )