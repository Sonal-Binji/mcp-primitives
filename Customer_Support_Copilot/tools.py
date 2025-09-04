# tools.py
"""
Enhanced MCP Tools Server with linked ticket/order relationships
Using FastMCP for simplified server creation
"""
from fastmcp import FastMCP
import json

# Enhanced mock database with linked relationships
TICKETS = {
    "123": {
        "status": "in_progress", 
        "issue": "Product defective - Widget A not working", 
        "customer": "john_doe", 
        "priority": "high",
        "order_id": "ORD001",
        "created_date": "2025-01-20",
        "last_updated": "2025-01-22"
    },
    "456": {
        "status": "resolved", 
        "issue": "Shipping delay - package arrived 3 days late", 
        "customer": "jane_smith", 
        "priority": "medium",
        "order_id": "ORD002",
        "created_date": "2025-01-18",
        "resolved_date": "2025-01-21"
    },
    "789": {
        "status": "pending", 
        "issue": "Wrong item received - ordered Device Y but got Cable Z", 
        "customer": "bob_wilson", 
        "priority": "low",
        "order_id": "ORD003",
        "created_date": "2025-01-23"
    }
}

ORDERS = {
    "ORD001": {
        "customer": "john_doe", 
        "items": ["Widget A", "Gadget B"], 
        "status": "delivered", 
        "total": 299.99,
        "order_date": "2025-01-15",
        "delivery_date": "2025-01-19",
        "tracking_number": "1Z999AA1234567890",
        "related_tickets": ["123"]
    },
    "ORD002": {
        "customer": "jane_smith", 
        "items": ["Tool X"], 
        "status": "delivered", 
        "total": 49.99,
        "order_date": "2025-01-16",
        "delivery_date": "2025-01-21",
        "tracking_number": "1Z999BB1234567890",
        "related_tickets": ["456"]
    },
    "ORD003": {
        "customer": "bob_wilson", 
        "items": ["Device Y", "Cable Z"], 
        "status": "delivered", 
        "total": 199.99,
        "order_date": "2025-01-17",
        "delivery_date": "2025-01-22",
        "tracking_number": "1Z999CC1234567890",
        "related_tickets": ["789"]
    }
}

CUSTOMERS = {
    "john_doe": {
        "name": "John Doe", 
        "email": "john@example.com", 
        "tier": "premium", 
        "orders": ["ORD001"],
        "tickets": ["123"],
        "phone": "+1-555-0101",
        "address": "123 Main St, Anytown USA"
    },
    "jane_smith": {
        "name": "Jane Smith", 
        "email": "jane@example.com", 
        "tier": "standard", 
        "orders": ["ORD002"],
        "tickets": ["456"],
        "phone": "+1-555-0102",
        "address": "456 Oak Ave, Somewhere USA"
    }, 
    "bob_wilson": {
        "name": "Bob Wilson", 
        "email": "bob@example.com", 
        "tier": "standard", 
        "orders": ["ORD003"],
        "tickets": ["789"],
        "phone": "+1-555-0103",
        "address": "789 Pine Rd, Elsewhere USA"
    }
}

# Create FastMCP server
mcp = FastMCP("Enhanced Customer Support Tools")

@mcp.tool()
def get_ticket_status(ticket_id: str) -> str:
    """Get the status and details of a support ticket, including linked order info"""
    if ticket_id in TICKETS:
        ticket = TICKETS[ticket_id].copy()
        
        # Add linked order information if available
        if "order_id" in ticket and ticket["order_id"] in ORDERS:
            ticket["linked_order"] = ORDERS[ticket["order_id"]]
            
        # Add customer information
        if "customer" in ticket and ticket["customer"] in CUSTOMERS:
            customer = CUSTOMERS[ticket["customer"]]
            ticket["customer_info"] = {
                "name": customer["name"],
                "tier": customer["tier"],
                "email": customer["email"]
            }
            
        return json.dumps(ticket, indent=2)
    else:
        return f"Ticket {ticket_id} not found"

@mcp.tool()
def get_order_info(order_id: str) -> str:
    """Get order information including items, status, and related tickets"""
    if order_id in ORDERS:
        order = ORDERS[order_id].copy()
        
        # Add related ticket information if available
        if "related_tickets" in order:
            related_tickets = []
            for ticket_id in order["related_tickets"]:
                if ticket_id in TICKETS:
                    related_tickets.append({
                        "ticket_id": ticket_id,
                        "status": TICKETS[ticket_id]["status"],
                        "issue": TICKETS[ticket_id]["issue"],
                        "priority": TICKETS[ticket_id]["priority"]
                    })
            order["ticket_details"] = related_tickets
            
        # Add customer information
        if "customer" in order and order["customer"] in CUSTOMERS:
            customer = CUSTOMERS[order["customer"]]
            order["customer_info"] = {
                "name": customer["name"],
                "tier": customer["tier"],
                "email": customer["email"]
            }
            
        return json.dumps(order, indent=2)
    else:
        return f"Order {order_id} not found"

@mcp.tool()
def get_customer_details(customer_id: str) -> str:
    """Get customer information including name, email, tier, and complete history"""
    if customer_id in CUSTOMERS:
        customer = CUSTOMERS[customer_id].copy()
        
        # Add detailed order information
        detailed_orders = []
        for order_id in customer.get("orders", []):
            if order_id in ORDERS:
                order = ORDERS[order_id]
                detailed_orders.append({
                    "order_id": order_id,
                    "status": order["status"],
                    "total": order["total"],
                    "items": order["items"],
                    "order_date": order["order_date"]
                })
        customer["order_details"] = detailed_orders
        
        # Add detailed ticket information
        detailed_tickets = []
        for ticket_id in customer.get("tickets", []):
            if ticket_id in TICKETS:
                ticket = TICKETS[ticket_id]
                detailed_tickets.append({
                    "ticket_id": ticket_id,
                    "status": ticket["status"],
                    "issue": ticket["issue"],
                    "priority": ticket["priority"],
                    "created_date": ticket["created_date"]
                })
        customer["ticket_details"] = detailed_tickets
        
        return json.dumps(customer, indent=2)
    else:
        return f"Customer {customer_id} not found"

@mcp.tool()
def initiate_return(reference_id: str, reason: str = "No reason provided") -> str:
    """Initiate a return process for an order or ticket"""
    # Check if it's a ticket or order
    if reference_id in TICKETS:
        ticket = TICKETS[reference_id]
        result = {
            "return_initiated": True,
            "type": "ticket_return",
            "reference": reference_id,
            "reason": reason,
            "return_id": f"RET_{reference_id}",
            "estimated_processing": "3-5 business days",
            "customer": ticket["customer"],
            "linked_order": ticket.get("order_id", "N/A")
        }
    elif reference_id in ORDERS:
        order = ORDERS[reference_id]
        result = {
            "return_initiated": True,
            "type": "order_return", 
            "reference": reference_id,
            "reason": reason,
            "return_id": f"RET_{reference_id}",
            "estimated_processing": "5-7 business days",
            "customer": order["customer"],
            "items": order["items"],
            "order_value": order["total"]
        }
    else:
        result = {"error": f"Reference {reference_id} not found"}
    
    return json.dumps(result, indent=2)

@mcp.tool()
def escalate_ticket(ticket_id: str, department: str, notes: str = "") -> str:
    """Escalate a ticket to higher priority or different department"""
    if ticket_id in TICKETS:
        ticket = TICKETS[ticket_id]
        result = {
            "escalated": True,
            "ticket_id": ticket_id,
            "escalated_to": department,
            "escalation_id": f"ESC_{ticket_id}",
            "notes": notes,
            "estimated_response": "Within 24 hours",
            "original_priority": ticket["priority"],
            "customer": ticket["customer"],
            "linked_order": ticket.get("order_id", "N/A")
        }
        # Update ticket priority
        TICKETS[ticket_id]["priority"] = "urgent"
        TICKETS[ticket_id]["escalated_to"] = department
        return json.dumps(result, indent=2)
    else:
        return json.dumps({"error": f"Ticket {ticket_id} not found"})

@mcp.tool()
def search_by_customer(customer_name: str) -> str:
    """Find customer by name and return their details"""
    for customer_id, customer_data in CUSTOMERS.items():
        if customer_data["name"].lower() == customer_name.lower():
            return get_customer_details(customer_id)
    
    # Partial name matching
    matches = []
    for customer_id, customer_data in CUSTOMERS.items():
        if customer_name.lower() in customer_data["name"].lower():
            matches.append({
                "customer_id": customer_id,
                "name": customer_data["name"],
                "email": customer_data["email"],
                "tier": customer_data["tier"]
            })
    
    if matches:
        return json.dumps({"partial_matches": matches}, indent=2)
    else:
        return f"No customer found matching '{customer_name}'"

if __name__ == "__main__":
    # Run server with streamable-http transport
    mcp.run(transport="streamable-http", port=8001)