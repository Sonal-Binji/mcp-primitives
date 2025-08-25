# prompts.py
'''MCP Prompts Server - Covers prompt templates for customer support use cases
Using FastMCP for simplified server creation
'''
from fastmcp import FastMCP

# Create FastMCP server
mcp = FastMCP("Customer Support Prompts")

@mcp.prompt()
def customer_greeting(customer_name: str = "Not specified", customer_tier: str = "Not specified", issue_type: str = "Not specified") -> str:
    """Generate a personalized greeting for customers"""
    return f"""
You are a friendly customer support representative. Generate a warm, personalized greeting for the customer.

Customer Information:
- Name: {customer_name}
- Tier: {customer_tier}
- Issue Type: {issue_type}

Create a greeting that:
1. Welcomes the customer warmly
2. Acknowledges their tier status appropriately
3. Shows readiness to help with their specific issue type
4. Sets a positive, helpful tone

Keep it concise but genuine.
    """

@mcp.prompt()
def issue_analysis(issue_description: str, customer_history: str = "Not specified", urgency_level: str = "Not specified") -> str:
    """Analyze customer issues and suggest solutions"""
    return f"""
You are an expert customer support analyst. Analyze the following customer issue and provide actionable recommendations.

Issue Details:
- Description: {issue_description}
- Customer History: {customer_history}
- Urgency Level: {urgency_level}

Provide analysis including:
1. Root cause assessment
2. Immediate action steps
3. Long-term resolution plan
4. Escalation recommendations if needed
5. Prevention strategies for future

Be thorough but practical in your analysis.
    """

@mcp.prompt()
def policy_explanation(policy_content: str, customer_situation: str, tone: str = "professional") -> str:
    """Explain company policies in customer-friendly language"""
    return f"""
You are a customer support specialist. Explain the relevant company policy to the customer in a clear, helpful way.

Policy Content:
{policy_content}

Customer Situation:
{customer_situation}

Communication Tone: {tone}

Tasks:
1. Extract the parts of the policy most relevant to the customer's situation
2. Explain it in simple, friendly language
3. Highlight what this means for their specific case
4. Mention any exceptions or special considerations that might apply
5. Offer next steps or alternatives if the policy doesn't favor them

Make it clear and actionable, not bureaucratic.
    """

@mcp.prompt()
def follow_up_email(interaction_summary: str, resolution_status: str, next_steps: str = "Not specified", customer_name: str = "Not specified") -> str:
    """Generate follow-up emails for customer interactions"""
    return f"""
Create a professional follow-up email for a customer support interaction.

Interaction Details:
- Summary: {interaction_summary}
- Resolution Status: {resolution_status}
- Next Steps: {next_steps}
- Customer: {customer_name}

Email should include:
1. Appreciation for their patience/time
2. Summary of what was discussed
3. Current status of their issue
4. Clear next steps and timeline
5. Contact information for further questions
6. Professional but warm closing

Keep it concise and actionable.
    """

@mcp.prompt()
def escalation_brief(case_details: str, attempted_solutions: str, escalation_reason: str, urgency: str = "Not specified") -> str:
    """Create briefing documents for escalated cases"""
    return f"""
Create a comprehensive escalation brief for a customer support case.

Case Information:
- Details: {case_details}
- Solutions Attempted: {attempted_solutions}
- Escalation Reason: {escalation_reason}
- Urgency: {urgency}

Brief should include:
1. Executive summary (2-3 sentences)
2. Customer background and history
3. Issue timeline and chronology
4. Solutions attempted and outcomes
5. Current status and roadblocks
6. Recommended actions and alternatives
7. Business impact assessment
8. Required resources or approvals

Format for quick executive review while providing complete context.
    """

if __name__ == "__main__":
    # Run server with streamable-http transport
    mcp.run(transport="streamable-http", port=8003)