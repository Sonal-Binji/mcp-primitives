# conversational_copilot_improved.py
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
    current_context: Dict[str, Any] = field(default_factory=dict)
    
    def add_ticket(self, ticket_id: str):
        if ticket_id not in self.ticket_ids:
            self.ticket_ids.append(ticket_id)
    
    def add_order(self, order_id: str):
        if order_id not in self.order_ids:
            self.order_ids.append(order_id)
    
    def add_customer(self, customer_id: str):
        if customer_id not in self.customer_ids:
            self.customer_ids.append(customer_id)
    
    def get_context_summary(self) -> str:
        context_parts = []
        if self.ticket_ids:
            context_parts.append(f"Known tickets: {', '.join(self.ticket_ids)}")
        if self.order_ids:
            context_parts.append(f"Known orders: {', '.join(self.order_ids)}")
        if self.customer_ids:
            context_parts.append(f"Known customers: {', '.join(self.customer_ids)}")
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
                
                # Debug output
                print(f"DEBUG: Reading resource {resource_uri}")
                print(f"DEBUG: Response type: {type(res)}")
                print(f"DEBUG: Has contents: {hasattr(res, 'contents')}")
                
                texts: List[str] = []
                
                # Handle different response formats
                if hasattr(res, 'contents') and res.contents:
                    print(f"DEBUG: Contents count: {len(res.contents)}")
                    for i, item in enumerate(res.contents):
                        print(f"DEBUG: Content {i} type: {type(item)}")
                        
                        # Handle text content
                        if hasattr(item, 'text') and item.text:
                            texts.append(item.text)
                            print(f"DEBUG: Added text from item.text: {len(item.text)} chars")
                        elif isinstance(item, dict) and item.get('text'):
                            texts.append(item['text'])
                            print(f"DEBUG: Added text from dict: {len(item['text'])} chars")
                        elif hasattr(item, 'type') and item.type == 'text':
                            if hasattr(item, 'text'):
                                texts.append(item.text)
                                print(f"DEBUG: Added text from typed item: {len(item.text)} chars")
                
                # Fallback: check if res itself has text
                elif hasattr(res, 'text') and res.text:
                    texts.append(res.text)
                    print(f"DEBUG: Added text from direct response: {len(res.text)} chars")
                
                # Another fallback: check if it's a string response
                elif isinstance(res, str):
                    texts.append(res)
                    print(f"DEBUG: Response is direct string: {len(res)} chars")
                
                result = "\n".join(texts).strip()
                print(f"DEBUG: Final result length: {len(result)} chars")
                
                if result:
                    return result
                else:
                    # Debug: show all attributes of the response
                    attrs = [attr for attr in dir(res) if not attr.startswith('_')]
                    return f"No content found for resource: {resource_uri}. Available attributes: {attrs}"
                
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
    # Extract ticket IDs (format: numbers like 123, 456)
    ticket_matches = re.findall(r'\b\d{3,4}\b', response)
    for ticket_id in ticket_matches:
        memory.add_ticket(ticket_id)
    
    # Extract order IDs (format: ORD followed by numbers)
    order_matches = re.findall(r'\bORD\d+\b', response, re.IGNORECASE)
    for order_id in order_matches:
        memory.add_order(order_id)
    
    # Extract customer IDs (format: word_word like john_doe)
    customer_matches = re.findall(r'\b[a-z]+_[a-z]+\b', response, re.IGNORECASE)
    for customer_id in customer_matches:
        memory.add_customer(customer_id.lower())

class TicketInput(BaseModel):
    ticket_id: str = Field(..., description="The ticket ID to look up")

def get_ticket_status_tool(ticket_id: str) -> str:
    """Get ticket status and remember the ticket ID"""
    memory.add_ticket(ticket_id)
    result = asyncio.run(_mcp_call_tool("get_ticket_status", {"ticket_id": ticket_id}, TOOLS_URL))
    extract_ids_from_response(result)
    return result

class OrderInput(BaseModel):
    order_id: str = Field(..., description="The order ID to look up")

def get_order_info_tool(order_id: str) -> str:
    """Get order information and remember the order ID"""
    memory.add_order(order_id)
    result = asyncio.run(_mcp_call_tool("get_order_info", {"order_id": order_id}, TOOLS_URL))
    extract_ids_from_response(result)
    return result

class CustomerInput(BaseModel):
    customer_id: str = Field(..., description="The customer ID to look up")

def get_customer_details_tool(customer_id: str) -> str:
    """Get customer details and remember the customer ID"""
    memory.add_customer(customer_id)
    result = asyncio.run(_mcp_call_tool("get_customer_details", {"customer_id": customer_id}, TOOLS_URL))
    extract_ids_from_response(result)
    return result

class PolicyInput(BaseModel):
    policy_type: str = Field(..., description="Policy type: shipping_policy, return_policy, refund_policy, warranty_policy, or list_all")

def get_policy_tool(policy_type: str) -> str:
    """Retrieve company policy documents from database"""
    print(f"DEBUG: get_policy_tool called with policy_type: {policy_type}")
    
    # Map common variations to correct policy names
    policy_mapping = {
        "shipping": "shipping_policy",
        "return": "return_policy", 
        "returns": "return_policy",
        "refund": "refund_policy",
        "refunds": "refund_policy",
        "warranty": "warranty_policy",
        "warranties": "warranty_policy",
        "list": "list_all",
        "all": "list_all"
    }
    
    # Normalize policy type
    normalized_policy = policy_mapping.get(policy_type.lower(), policy_type.lower())
    if not normalized_policy.endswith("_policy") and normalized_policy != "list_all":
        normalized_policy += "_policy"
    
    print(f"DEBUG: Normalized policy: {normalized_policy}")
    
    resource_uri = f"policy://{normalized_policy}"
    result = asyncio.run(_mcp_read_resource(resource_uri, RESOURCES_URL))
    
    print(f"DEBUG: Policy result length: {len(result)} chars")
    
    return result

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

class PromptInput(BaseModel):
    prompt_name: str = Field(..., description="Name of the prompt template")
    customer_name: str = Field(default="", description="Customer name")
    issue_description: str = Field(default="", description="Description of the issue")
    customer_tier: str = Field(default="standard", description="Customer tier")
    urgency_level: str = Field(default="medium", description="Urgency level")

def get_support_prompt_tool(prompt_name: str, customer_name: str = "", issue_description: str = "", 
                          customer_tier: str = "standard", urgency_level: str = "medium") -> str:
    """Get a support prompt template"""
    args = {
        "customer_name": customer_name,
        "issue_description": issue_description,
        "customer_tier": customer_tier,
        "urgency_level": urgency_level
    }
    return asyncio.run(_mcp_get_prompt(prompt_name, args, PROMPTS_URL))

# ---------- Direct Policy Functions ----------

async def get_policy_direct(policy_type: str) -> str:
    """Direct function to get policy without using tools framework"""
    policy_mapping = {
        "shipping": "shipping_policy",
        "return": "return_policy", 
        "returns": "return_policy",
        "refund": "refund_policy",
        "refunds": "refund_policy",
        "warranty": "warranty_policy",
        "warranties": "warranty_policy",
        "list": "list_all",
        "all": "list_all"
    }
    
    normalized_policy = policy_mapping.get(policy_type.lower(), policy_type.lower())
    if not normalized_policy.endswith("_policy") and normalized_policy != "list_all":
        normalized_policy += "_policy"
    
    resource_uri = f"policy://{normalized_policy}"
    return await _mcp_read_resource(resource_uri, RESOURCES_URL)

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
            func=get_policy_tool,
            name="get_policy",
            description="Get company policy documents from database. Use: shipping_policy, return_policy, refund_policy, warranty_policy, or list_all",
            args_schema=PolicyInput
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
            func=get_support_prompt_tool,
            name="get_support_prompt",
            description="Get support prompt templates for various scenarios",
            args_schema=PromptInput
        )
    ]

def create_agent():
    """Create the conversational agent with memory-aware system prompt"""
    llm = ChatGroq(
        groq_api_key=os.getenv("GROQ_API_KEY"),
        model="llama-3.3-70b-versatile",
        temperature=0.1,  # Lower temperature for more consistent tool usage
    )
    
    tools = create_tools()
    
    def create_system_message():
        base_prompt = """You are a helpful customer support assistant with access to various tools and company information.

IMPORTANT: When users ask about policies, you MUST use the get_policy tool to retrieve the actual policy content from the database. Always show the complete policy information to users.

Key behaviors:
1. Be conversational and helpful
2. Use the remembered context from previous interactions
3. When users mention ticket IDs, order IDs, or customer IDs, automatically look them up
4. When asked about policies (shipping, return, refund, warranty), ALWAYS use the get_policy tool
5. Provide complete, detailed responses using the tool results
6. Ask clarifying questions when needed
7. Link related information (tickets to orders, customers to their data)

Available tools allow you to:
- Look up ticket status and details
- Get order information
- Retrieve customer details  
- Access company policies from SQLite database (shipping_policy, return_policy, refund_policy, warranty_policy)
- Initiate returns
- Escalate tickets
- Generate support prompts

Current conversation context: """ + memory.get_context_summary()
        
        return base_prompt
    
    agent = create_react_agent(model=llm, tools=tools)
    
    # Store the system message creator for dynamic updates
    agent._create_system_message = create_system_message
    
    return agent

async def process_query(agent, user_input: str) -> str:
    """Process a user query and return the response"""
    # Extract any IDs from user input and remember them
    extract_ids_from_response(user_input)
    
    # Check if user is asking for policy directly - handle it without agent if needed
    policy_keywords = ["policy", "return", "shipping", "refund", "warranty"]
    if any(keyword in user_input.lower() for keyword in policy_keywords):
        print("DEBUG: Policy-related query detected")
        
        # Try to identify specific policy type
        if "return policy" in user_input.lower():
            policy_result = await get_policy_direct("return_policy")
            if policy_result and not policy_result.startswith("Error") and not policy_result.startswith("No content"):
                return f"Here's our return policy:\n\n{policy_result}"
        elif "shipping" in user_input.lower():
            policy_result = await get_policy_direct("shipping_policy")
            if policy_result and not policy_result.startswith("Error") and not policy_result.startswith("No content"):
                return f"Here's our shipping policy:\n\n{policy_result}"
        elif "refund" in user_input.lower():
            policy_result = await get_policy_direct("refund_policy")
            if policy_result and not policy_result.startswith("Error") and not policy_result.startswith("No content"):
                return f"Here's our refund policy:\n\n{policy_result}"
        elif "warranty" in user_input.lower():
            policy_result = await get_policy_direct("warranty_policy")
            if policy_result and not policy_result.startswith("Error") and not policy_result.startswith("No content"):
                return f"Here's our warranty policy:\n\n{policy_result}"
    
    # Create dynamic system message with current context
    system_message = agent._create_system_message()
    
    try:
        result = await agent.ainvoke({
            "messages": [
                SystemMessage(content=system_message),
                HumanMessage(content=user_input)
            ]
        })
        
        # Extract IDs from the response too
        response = result["messages"][-1].content
        extract_ids_from_response(response)
        
        return response
        
    except Exception as e:
        return f"Sorry, I encountered an error: {str(e)}"

def print_welcome():
    """Print welcome message and instructions"""
    print("\n" + "="*60)
    print("🎧 CUSTOMER SUPPORT COPILOT (IMPROVED)")
    print("="*60)
    print("Welcome! I'm your AI customer support assistant.")
    print("\nI can help you with:")
    print("• Looking up tickets, orders, and customer details")
    print("• Accessing company policies (now stored in SQLite database)")
    print("• Processing returns and escalations")
    print("• Generating support responses")
    print("\nJust ask me anything! I'll remember context as we chat.")
    print("Type 'quit', 'exit', or 'bye' to end the conversation.")
    print("Type 'memory' to see what I remember about our conversation.")
    print("Type 'test-policy' to test policy reading directly.")
    print("-" * 60)

def print_memory_status():
    """Print current memory status"""
    print("\n📝 CONVERSATION MEMORY:")
    print(f"  Tickets: {', '.join(memory.ticket_ids) if memory.ticket_ids else 'None'}")
    print(f"  Orders: {', '.join(memory.order_ids) if memory.order_ids else 'None'}")
    print(f"  Customers: {', '.join(memory.customer_ids) if memory.customer_ids else 'None'}")
    print()

async def test_policy_reading():
    """Test policy reading directly"""
    print("\n🧪 TESTING POLICY READING...")
    print("=" * 40)
    
    policies = ["shipping_policy", "return_policy", "refund_policy", "warranty_policy"]
    
    for policy in policies:
        print(f"\nTesting {policy}:")
        result = await get_policy_direct(policy)
        if result:
            preview = result[:200] + "..." if len(result) > 200 else result
            print(f"✅ Success: {len(result)} characters")
            print(f"Preview: {preview}")
        else:
            print("❌ Failed or empty result")
    
    print("\n" + "=" * 40)

async def main():
    """Main conversation loop"""
    print_welcome()
    
    agent = create_agent()
    
    while True:
        try:
            # Get user input
            user_input = input("\n💬 You: ").strip()
            
            # Handle special commands
            if user_input.lower() in ['quit', 'exit', 'bye']:
                print("\n👋 Thanks for using Customer Support Copilot! Have a great day!")
                break
            
            if user_input.lower() == 'memory':
                print_memory_status()
                continue
            
            if user_input.lower() == 'test-policy':
                await test_policy_reading()
                continue
                
            if not user_input:
                continue
            
            # Process the query
            print("\n🤖 Assistant: ", end="")
            response = await process_query(agent, user_input)
            print(response)
            
        except KeyboardInterrupt:
            print("\n\n👋 Thanks for using Customer Support Copilot! Have a great day!")
            break
        except Exception as e:
            print(f"\n❌ Error: {str(e)}")
            print("Please try again.")

if __name__ == "__main__":
    asyncio.run(main())