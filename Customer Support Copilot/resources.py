# resources.py
"""
MCP Resources Server - Provides company policies from SQLite database
Using FastMCP for simplified server creation
"""
import sqlite3
from pathlib import Path
from fastmcp import FastMCP

# --- Database Path ---
DB_PATH = str(Path(__file__).parent / "policies.db")

# --- Create FastMCP server ---
mcp = FastMCP("Customer Support Resources")


def get_policy_from_db(policy_type: str) -> str:
    """Retrieve policy content from database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT title, content FROM policies 
            WHERE policy_type = ?
        """, (policy_type,))
        result = cursor.fetchone()
        if result:
            title, content = result
            return f"{title}\n{'-' * len(title)}\n\n{content}"
        else:
            return f"Policy '{policy_type}' not found in database."
    except sqlite3.Error as e:
        return f"Database error: {str(e)}"
    finally:
        conn.close()


def list_all_policies() -> str:
    """List all available policies"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT policy_type, title FROM policies ORDER BY policy_type
        """)
        results = cursor.fetchall()
        if results:
            return "Available Policies:\n" + "\n".join(
                f"- {ptype}: {title}" for ptype, title in results
            )
        else:
            return "No policies found in database."
    except sqlite3.Error as e:
        return f"Database error: {str(e)}"
    finally:
        conn.close()


# --- Expose policies as resources ---
@mcp.resource("policy://shipping_policy")
def shipping_policy() -> str:
    return get_policy_from_db("shipping_policy")

@mcp.resource("policy://return_policy")
def return_policy() -> str:
    return get_policy_from_db("return_policy")

@mcp.resource("policy://refund_policy")
def refund_policy() -> str:
    return get_policy_from_db("refund_policy")

@mcp.resource("policy://warranty_policy")
def warranty_policy() -> str:
    return get_policy_from_db("warranty_policy")

@mcp.resource("policy://list_all")
def list_policies() -> str:
    return list_all_policies()


if __name__ == "__main__":
    # Run server with streamable-http transport
    mcp.run(transport="streamable-http", port=8002)
