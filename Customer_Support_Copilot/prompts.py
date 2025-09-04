# enhanced_prompts_server.py
"""
Enhanced MCP Prompts Server for user-friendly, brief policy explanations
"""
from fastmcp import FastMCP
import json
from typing import Dict, Any, Optional

# Create FastMCP server
mcp = FastMCP("Smart Customer Support Prompts")

def parse_customer_context(customer_situation: str) -> Dict[str, Any]:
    """Parse customer situation string into structured data"""
    context = {
        "customer_name": None,
        "tier": "standard",
        "recent_orders": [],
        "recent_issues": [],
        "has_premium": False,
        "order_id": None,
        "items": []
    }
    
    # Extract customer name
    if "Customer:" in customer_situation:
        name_part = customer_situation.split("Customer:")[1].split("(")[0].strip()
        context["customer_name"] = name_part
    
    # Extract tier
    if "premium" in customer_situation.lower():
        context["tier"] = "premium"
        context["has_premium"] = True
    
    # Extract order info
    if "order" in customer_situation.lower():
        import re
        order_match = re.search(r'order (\w+)', customer_situation, re.IGNORECASE)
        if order_match:
            context["order_id"] = order_match.group(1)
        
        # Extract items if present
        if ":" in customer_situation:
            items_part = customer_situation.split(":")[-1].strip()
            context["items"] = [item.strip() for item in items_part.split(",")]
    
    return context

@mcp.prompt()
def policy_explanation(
    policy_content: str, 
    customer_situation: str = "General inquiry", 
    tone: str = "friendly"
) -> str:
    """Generate brief, user-friendly policy explanations with customer-specific details"""
    
    context = parse_customer_context(customer_situation)
    
    # Build personalized greeting
    greeting = ""
    if context["customer_name"]:
        greeting = f"Hi {context['customer_name']}, "
        if context["has_premium"]:
            greeting += "as a premium customer, "
    
    # Build context-aware instructions
    context_instructions = ""
    if context["order_id"]:
        context_instructions = f"""
CUSTOMER CONTEXT: This customer is asking about their order {context['order_id']}.
Make the policy explanation relevant to their specific order situation.
"""
    
    if context["has_premium"]:
        context_instructions += """
PREMIUM CUSTOMER: Highlight any premium benefits or faster processing times they get.
"""
    
    return f"""You are explaining company policy in a helpful, conversational way.

{greeting}Here's what you need to know about our policy:

POLICY CONTENT:
{policy_content}

CUSTOMER SITUATION:
{customer_situation}

{context_instructions}

INSTRUCTIONS:
1. Extract ONLY the most relevant parts of the policy for this customer
2. Explain in 2-4 bullet points maximum
3. Use simple, conversational language (no corporate jargon)  
4. Focus on what THEY CAN DO, not restrictions
5. If premium customer, mention any special benefits
6. If they have a specific order/item, relate policy to that
7. End with ONE clear next step they can take
8. Keep total response under 100 words

TONE: {tone} and helpful

Make it feel like you're talking to a friend, not reading from a manual."""

@mcp.prompt()
def contextual_response(
    query: str,
    customer_data: str = "",
    order_data: str = "",
    tone: str = "friendly"
) -> str:
    """Generate brief contextual responses that reference specific details"""
    
    return f"""You are responding to a customer query in a personal, helpful way.

CUSTOMER QUERY: {query}

CUSTOMER INFO: {customer_data}
ORDER INFO: {order_data}

RESPONSE STYLE: {tone}

INSTRUCTIONS:
1. Answer their question directly in 2-3 sentences
2. Use their name if available
3. Reference specific details (order numbers, dates, items) when relevant
4. Show you understand their history
5. Keep it conversational and brief
6. End with what they should do next OR offer additional help
7. Maximum 75 words total

Make it feel like you actually looked at their account and remember them."""

@mcp.prompt()
def smart_greeting(
    customer_name: str = "",
    customer_tier: str = "standard",
    recent_activity: str = "",
    issue_type: str = ""
) -> str:
    """Generate brief, context-aware greetings"""
    
    return f"""Generate a warm but brief greeting for a customer.

CUSTOMER: {customer_name}
TIER: {customer_tier}
RECENT ACTIVITY: {recent_activity}
ISSUE TYPE: {issue_type}

GREETING GUIDELINES:
1. Use their name if available
2. Premium customers get acknowledged (but briefly)
3. Reference recent activity if relevant ("I see your recent order..." or "Following up on your inquiry...")
4. Show you're ready to help
5. Keep it under 30 words
6. Warm but professional tone

Examples:
- "Hi John! I see your recent order for the Widget A. How can I help?"
- "Hello Sarah! As a premium customer, you get priority support. What can I do for you?"
- "Hi! I noticed your recent inquiry about shipping. How can I assist today?"

Make it personal but not overly familiar."""

@mcp.prompt()
def escalation_summary(
    issue_summary: str,
    customer_tier: str = "standard",
    urgency: str = "medium",
    attempted_solutions: str = "",
    customer_name: str = ""
) -> str:
    """Generate concise escalation summaries for team handoffs"""
    
    return f"""Create a brief escalation summary for internal review.

ISSUE: {issue_summary}
CUSTOMER: {customer_name} ({customer_tier} tier)
URGENCY: {urgency}
TRIED: {attempted_solutions}

FORMAT YOUR SUMMARY AS:

**PRIORITY**: [HIGH/MEDIUM/LOW based on tier and urgency]
**CUSTOMER**: {customer_name} ({customer_tier})
**ISSUE**: [1-2 sentence summary]
**ATTEMPTED**: [What was tried]
**NEXT**: [Recommended action]
**TIMELINE**: [Response timeframe]

Keep it under 150 words total. Make it scannable for quick executive review."""

@mcp.prompt()
def follow_up_message(
    interaction_summary: str,
    resolution_status: str,
    customer_name: str = "",
    next_steps: str = ""
) -> str:
    """Generate brief, personal follow-up messages"""
    
    name_greeting = f"Hi {customer_name}," if customer_name else "Hi there,"
    
    return f"""Write a brief follow-up message to a customer.

INTERACTION: {interaction_summary}
STATUS: {resolution_status}
NEXT STEPS: {next_steps}
CUSTOMER: {customer_name}

MESSAGE STRUCTURE:
1. {name_greeting}
2. Brief recap (1 sentence)
3. Current status (1 sentence)
4. Next steps with timeline (1 sentence)
5. Contact info offer (1 sentence)

TONE: Warm, professional, and reassuring
TOTAL LENGTH: Under 100 words

Make them feel valued and kept in the loop without being wordy."""

@mcp.prompt()
def quick_policy_summary(
    policy_type: str,
    specific_question: str = ""
) -> str:
    """Generate ultra-brief policy summaries for quick reference"""
    
    return f"""Create a very brief policy summary.

POLICY TYPE: {policy_type}
SPECIFIC QUESTION: {specific_question}

INSTRUCTIONS:
1. Provide only the essential information
2. Use bullet points (max 3)
3. Focus on customer actions, not company rules
4. Include timeframes if relevant
5. Under 50 words total
6. Make it actionable

This is for quick reference during live conversations."""

if __name__ == "__main__":
    try:
        mcp.run(transport="streamable-http", port=8003)
    except Exception as e:
        print(f"Failed to start prompts server: {e}")