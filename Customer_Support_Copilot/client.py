# conversational_copilot_smart_policies.py
import os
import asyncio
import json
import re
from typing import List, Any, Dict, Optional
from dataclasses import dataclass, field

from pydantic import BaseModel, Field
from langchain.tools import StructuredTool
from langchain_groq import ChatGroq
from langgraph.prebuilt import create_react_agent
from langchain.schema import HumanMessage, AIMessage, SystemMessage

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

from dotenv import load_dotenv
load_dotenv()

# ---- MCP Endpoints ----
TOOLS_URL = "http://127.0.0.1:8001/mcp"    # tools server
RESOURCES_URL = "http://127.0.0.1:8002/mcp"  # resources server
PROMPTS_URL = "http://127.0.0.1:8003/mcp"   # prompts server

@dataclass
class ConversationMemory:
    """Manages conversation context and remembered entities"""
    ticket_ids: List[str] = field(default_factory=list)
    order_ids: List[str] = field(default_factory=list)
    customer_ids: List[str] = field(default_factory=list)
    customer_names: List[str] = field(default_factory=list)
    current_context: Dict[str, Any] = field(default_factory=dict)
    last_customer_data: Optional[str] = None
    last_order_data: Optional[str] = None
    
    def add_ticket(self, ticket_id: str):
        if ticket_id not in self.ticket_ids:
            self.ticket_ids.append(ticket_id)
    
    def add_order(self, order_id: str):
        if order_id not in self.order_ids:
            self.order_ids.append(order_id)
    
    def add_customer(self, customer_id: str):
        if customer_id not in self.customer_ids:
            self.customer_ids.append(customer_id)
    
    def add_customer_name(self, name: str):
        if name not in self.customer_names:
            self.customer_names.append(name)
    
    def get_recent_customer_name(self) -> str:
        return self.customer_names[-1] if self.customer_names else ""
    
    def get_recent_order_id(self) -> str:
        return self.order_ids[-1] if self.order_ids else ""
    
    def get_context_summary(self) -> str:
        context_parts = []
        if self.ticket_ids:
            context_parts.append(f"Tickets: {', '.join(self.ticket_ids[-3:])}")  # Last 3 only
        if self.order_ids:
            context_parts.append(f"Orders: {', '.join(self.order_ids[-3:])}")
        if self.customer_names:
            context_parts.append(f"Customer: {self.customer_names[-1]}")  # Most recent
        return " | ".join(context_parts) if context_parts else "No context"

# Global memory instance
memory = ConversationMemory()

# ---------- MCP Helpers ----------

async def _mcp_call_tool(tool_name: str, params: dict, url: str) -> str:
    """Call an MCP tool and return the response"""
    try:
        async with streamablehttp_client(url) as (read, write, _sid):
            async with ClientSession(read, write) as session:
                await session.initialize()
                resp = await session.call_tool(tool_name, params)
                if resp.content:
                    texts = [c.text for c in resp.content if getattr(c, "text", None)]
                    return "\n".join(texts)
                return f"No response from tool {tool_name}"
    except Exception as e:
        return f"Error calling tool {tool_name}: {str(e)}"

async def _mcp_read_resource(resource_uri: str, url: str) -> str:
    """Read an MCP resource and return the content"""
    try:
        async with streamablehttp_client(url) as (read, write, _sid):
            async with ClientSession(read, write) as session:
                await session.initialize()
                res = await session.read_resource(resource_uri)
                
                texts: List[str] = []
                
                if hasattr(res, 'contents') and res.contents:
                    for item in res.contents:
                        if hasattr(item, 'text') and item.text:
                            texts.append(item.text)
                        elif isinstance(item, dict) and item.get('text'):
                            texts.append(item['text'])
                
                result = "\n".join(texts).strip()
                return result if result else f"No content found for resource: {resource_uri}"
                
    except Exception as e:
        return f"Error reading resource {resource_uri}: {str(e)}"

async def _mcp_get_prompt(prompt_name: str, args: dict, url: str) -> str:
    """Get an MCP prompt with arguments"""
    try:
        async with streamablehttp_client(url) as (read, write, _sid):
            async with ClientSession(read, write) as session:
                await session.initialize()
                
                result = await session.get_prompt(prompt_name, args)
                
                pieces: List[str] = []
                
                if hasattr(result, 'messages') and result.messages:
                    for msg in result.messages:
                        if hasattr(msg, 'content') and msg.content:
                            for c in msg.content:
                                if hasattr(c, 'text') and c.text:
                                    pieces.append(c.text)
                                elif isinstance(c, dict) and c.get('text'):
                                    pieces.append(c['text'])
                
                return "\n".join(pieces).strip()
                
    except Exception as e:
        return f"Error getting prompt {prompt_name}: {str(e)}"

# ---------- Enhanced Tool Wrappers ----------

def extract_ids_from_response(response: str) -> None:
    """Extract and remember ticket/order/customer IDs from responses"""
    # Extract ticket IDs
    ticket_matches = re.findall(r'\b\d{3,4}\b', response)
    for ticket_id in ticket_matches:
        memory.add_ticket(ticket_id)
    
    # Extract order IDs
    order_matches = re.findall(r'\bORD\d+\b', response, re.IGNORECASE)
    for order_id in order_matches:
        memory.add_order(order_id)
    
    # Extract customer IDs
    customer_matches = re.findall(r'\b[a-z]+_[a-z]+\b', response, re.IGNORECASE)
    for customer_id in customer_matches:
        memory.add_customer(customer_id.lower())
    
    # Extract customer names (like "John Doe", "Jane Smith")
    name_matches = re.findall(r'"([A-Z][a-z]+ [A-Z][a-z]+)"', response)
    for name in name_matches:
        memory.add_customer_name(name)

class TicketInput(BaseModel):
    ticket_id: str = Field(..., description="The ticket ID to look up")

def get_ticket_status_tool(ticket_id: str) -> str:
    """Get ticket status and remember the ticket ID"""
    memory.add_ticket(ticket_id)
    result = asyncio.run(_mcp_call_tool("get_ticket_status", {"ticket_id": ticket_id}, TOOLS_URL))
    extract_ids_from_response(result)
    
    # Store for context
    memory.current_context['last_ticket'] = result
    return result

class OrderInput(BaseModel):
    order_id: str = Field(..., description="The order ID to look up")

def get_order_info_tool(order_id: str) -> str:
    """Get order information and remember the order ID"""
    memory.add_order(order_id)
    result = asyncio.run(_mcp_call_tool("get_order_info", {"order_id": order_id}, TOOLS_URL))
    extract_ids_from_response(result)
    
    # Store for context
    memory.last_order_data = result
    memory.current_context['last_order'] = result
    return result

class CustomerInput(BaseModel):
    customer_id: str = Field(..., description="The customer ID to look up")

def get_customer_details_tool(customer_id: str) -> str:
    """Get customer details and remember the customer ID"""
    memory.add_customer(customer_id)
    result = asyncio.run(_mcp_call_tool("get_customer_details", {"customer_id": customer_id}, TOOLS_URL))
    extract_ids_from_response(result)
    
    # Store for context
    memory.last_customer_data = result
    memory.current_context['last_customer'] = result
    return result

class SmartPolicyInput(BaseModel):
    policy_type: str = Field(..., description="Policy type: shipping, return, refund, warranty")
    context_type: str = Field(default="general", description="Context: general, order_specific, ticket_specific")
    customer_situation: str = Field(default="", description="Customer's current situation for personalized response")

def get_smart_policy_explanation_tool(policy_type: str, context_type: str = "general", customer_situation: str = "") -> str:
    """Get user-friendly, contextual policy explanation using prompts"""
    
    # Get raw policy content
    policy_mapping = {
        "shipping": "shipping_policy",
        "return": "return_policy", 
        "returns": "return_policy",
        "refund": "refund_policy",
        "refunds": "refund_policy", 
        "warranty": "warranty_policy"
    }
    
    normalized_policy = policy_mapping.get(policy_type.lower(), policy_type.lower())
    if not normalized_policy.endswith("_policy"):
        normalized_policy += "_policy"
    
    # Get raw policy content
    resource_uri = f"policy://{normalized_policy}"
    raw_policy = asyncio.run(_mcp_read_resource(resource_uri, RESOURCES_URL))
    
    if raw_policy.startswith("Error") or "not found" in raw_policy:
        return f"Sorry, I couldn't find the {policy_type} policy."
    
    # Build customer situation context
    if not customer_situation and memory.last_customer_data:
        try:
            customer_data = json.loads(memory.last_customer_data)
            customer_name = customer_data.get("name", "")
            customer_tier = customer_data.get("tier", "standard")
            customer_situation = f"Customer: {customer_name} ({customer_tier} tier)"
            
            # Add recent order info if available
            if memory.last_order_data:
                order_data = json.loads(memory.last_order_data)
                order_id = memory.get_recent_order_id()
                items = order_data.get("items", [])
                customer_situation += f" | Recent order {order_id}: {', '.join(items)}"
            
        except:
            customer_situation = "General inquiry"
    
    if not customer_situation:
        customer_situation = "General inquiry"
    
    # Use the policy explanation prompt
    prompt_args = {
        "policy_content": raw_policy,
        "customer_situation": customer_situation,
        "tone": "friendly"
    }
    
    return asyncio.run(_mcp_get_prompt("policy_explanation", prompt_args, PROMPTS_URL))

class ReturnInput(BaseModel):
    reference_id: str = Field(..., description="Ticket or order ID to process return for")
    reason: str = Field(default="Customer request", description="Reason for return")

def initiate_return_tool(reference_id: str, reason: str = "Customer request") -> str:
    """Initiate a return process"""
    result = asyncio.run(_mcp_call_tool("initiate_return", {"reference_id": reference_id, "reason": reason}, TOOLS_URL))
    extract_ids_from_response(result)
    return result

class EscalationInput(BaseModel):
    ticket_id: str = Field(..., description="Ticket ID to escalate")
    department: str = Field(..., description="Department to escalate to")
    notes: str = Field(default="", description="Additional notes for escalation")

def escalate_ticket_tool(ticket_id: str, department: str, notes: str = "") -> str:
    """Escalate a ticket to another department"""
    memory.add_ticket(ticket_id)
    result = asyncio.run(_mcp_call_tool("escalate_ticket", {"ticket_id": ticket_id, "department": department, "notes": notes}, TOOLS_URL))
    extract_ids_from_response(result)
    return result

class ContextualResponseInput(BaseModel):
    query: str = Field(..., description="Customer query to respond to")
    tone: str = Field(default="friendly", description="Response tone")

def generate_contextual_response_tool(query: str, tone: str = "friendly") -> str:
    """Generate contextual response using customer and order data from memory"""
    
    customer_data = memory.last_customer_data or ""
    order_data = memory.last_order_data or ""
    
    prompt_args = {
        "query": query,
        "customer_data": customer_data,
        "order_data": order_data, 
        "tone": tone
    }
    
    return asyncio.run(_mcp_get_prompt("contextual_response", prompt_args, PROMPTS_URL))

class SmartGreetingInput(BaseModel):
    issue_type: str = Field(default="", description="Type of issue customer has")

def generate_smart_greeting_tool(issue_type: str = "") -> str:
    """Generate smart greeting based on current context"""
    
    customer_name = memory.get_recent_customer_name()
    customer_tier = "standard"
    recent_activity = ""
    
    # Extract tier from customer data if available
    if memory.last_customer_data:
        try:
            customer_data = json.loads(memory.last_customer_data)
            customer_tier = customer_data.get("tier", "standard")
            
            # Build recent activity summary
            orders = customer_data.get("order_details", [])
            tickets = customer_data.get("ticket_details", [])
            
            if orders:
                latest_order = orders[-1]
                recent_activity += f"recent order {latest_order.get('order_id', '')}"
            
            if tickets:
                latest_ticket = tickets[-1]
                if recent_activity:
                    recent_activity += f" and ticket {latest_ticket.get('ticket_id', '')}"
                else:
                    recent_activity = f"ticket {latest_ticket.get('ticket_id', '')}"
                    
        except:
            pass
    
    prompt_args = {
        "customer_name": customer_name,
        "customer_tier": customer_tier,
        "recent_activity": recent_activity,
        "issue_type": issue_type
    }
    
    return asyncio.run(_mcp_get_prompt("smart_greeting", prompt_args, PROMPTS_URL))

# ---------- Create Structured Tools ----------

def create_tools():
    """Create all the structured tools for the agent"""
    return [
        StructuredTool.from_function(
            func=get_ticket_status_tool,
            name="get_ticket_status",
            description="Get status and details of a support ticket by ID",
            args_schema=TicketInput
        ),
        StructuredTool.from_function(
            func=get_order_info_tool,
            name="get_order_info", 
            description="Get order information including items, status, and total",
            args_schema=OrderInput
        ),
        StructuredTool.from_function(
            func=get_customer_details_tool,
            name="get_customer_details",
            description="Get customer information including name, email, tier, and order history",
            args_schema=CustomerInput
        ),
        StructuredTool.from_function(
            func=get_smart_policy_explanation_tool,
            name="explain_policy",
            description="Get user-friendly policy explanation customized to customer's situation. Use for shipping, return, refund, or warranty policies.",
            args_schema=SmartPolicyInput
        ),
        StructuredTool.from_function(
            func=initiate_return_tool,
            name="initiate_return",
            description="Initiate a return process for a ticket or order",
            args_schema=ReturnInput
        ),
        StructuredTool.from_function(
            func=escalate_ticket_tool,
            name="escalate_ticket",
            description="Escalate a ticket to higher priority or different department",
            args_schema=EscalationInput
        ),
        StructuredTool.from_function(
            func=generate_contextual_response_tool,
            name="generate_response",
            description="Generate contextual response using remembered customer/order context",
            args_schema=ContextualResponseInput
        ),
        StructuredTool.from_function(
            func=generate_smart_greeting_tool,
            name="smart_greeting",
            description="Generate personalized greeting based on customer context",
            args_schema=SmartGreetingInput
        )
    ]

def create_agent():
    """Create the conversational agent with enhanced prompt integration"""
    llm = ChatGroq(
        groq_api_key=os.getenv("GROQ_API_KEY"),
        model="llama-3.3-70b-versatile",
        temperature=0.2,
    )
    
    tools = create_tools()
    
    def create_system_message():
        base_prompt = f"""You are a helpful customer support assistant with access to various tools and company information.

CORE BEHAVIOR:
1. Provide detailed, helpful responses for tickets, orders, customer inquiries, and general support
2. For POLICY QUESTIONS ONLY, use the explain_policy tool for brief, user-friendly explanations
3. Always personalize responses using customer context from previous interactions
4. Be thorough when explaining ticket status, order details, or troubleshooting
5. Use smart_greeting tool when starting conversations with new customers

POLICY HANDLING (ONLY FOR POLICY QUERIES):
- When users ask about shipping, return, refund, or warranty policies, use explain_policy tool
- This provides brief, customized explanations instead of raw policy text
- Focus on what the customer can do, not lengthy rules
- Relate policies to their specific orders/tickets when possible

GENERAL RESPONSE STYLE:
- Be conversational and thorough for non-policy questions
- Reference their name, order numbers, or ticket IDs when relevant
- Provide complete information for ticket status, order details, customer issues
- Ask clarifying questions when needed to help effectively
- Only keep responses brief when specifically dealing with policy explanations

Current context: {memory.get_context_summary()}
"""
        return base_prompt
    
    agent = create_react_agent(model=llm, tools=tools)
    agent._create_system_message = create_system_message
    
    return agent

async def process_query(agent, user_input: str) -> str:
    """Process a user query and return the response"""
    # Extract any IDs from user input
    extract_ids_from_response(user_input)
    
    # Create dynamic system message with current context
    system_message = agent._create_system_message()
    
    try:
        result = await agent.ainvoke({
            "messages": [
                SystemMessage(content=system_message),
                HumanMessage(content=user_input)
            ]
        })
        
        response = result["messages"][-1].content
        extract_ids_from_response(response)
        
        return response
        
    except Exception as e:
        return f"Sorry, I encountered an error: {str(e)}"

def print_welcome():
    """Print welcome message and instructions"""
    print("\n" + "="*60)
    print("SMART CUSTOMER SUPPORT COPILOT")
    print("="*60)
    print("I provide brief, personalized support using smart prompts!")
    print("\nI can help you with:")
    print("• Quick ticket, order, and customer lookups")
    print("• User-friendly policy explanations tailored to your situation")
    print("• Personalized responses based on your history")
    print("• Processing returns and escalations")
    print("\nType 'memory' to see conversation context.")
    print("Type 'quit' to exit.")
    print("-" * 60)

def print_memory_status():
    """Print current memory status"""
    print(f"\nContext: {memory.get_context_summary()}")

async def main():
    """Main conversation loop"""
    print_welcome()
    
    agent = create_agent()
    
    while True:
        try:
            user_input = input("\nYou: ").strip()
            
            if user_input.lower() in ['quit', 'exit', 'bye']:
                print("\nThanks for using Smart Customer Support! Goodbye!")
                break
            
            if user_input.lower() == 'memory':
                print_memory_status()
                continue
                
            if not user_input:
                continue
            
            print("\nAssistant: ", end="")
            response = await process_query(agent, user_input)
            print(response)
            
        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break
        except Exception as e:
            print(f"\nError: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())