# 🎧 Customer Support Copilot (MCP Use Case)

This project is a **Customer Support Copilot** built on the [Model Context Protocol (MCP)](https://modelcontextprotocol.io/).  
It demonstrates how tools, resources, and prompts can work together with an LLM to provide an **AI-powered customer support assistant**.

---

## ✨ Features
- **Tools Server (`tools.py`)**
  - Ticket lookup, escalation, and return initiation
  - Order info retrieval
  - Customer history lookup
  - Search by customer

- **Resources Server (`resources.py`)**
  - Company policies stored in SQLite (`policies.db`)
  - Resources exposed via MCP URIs

- **Prompts Server (`prompts.py`)**
  - Predefined prompt templates for support flows (greeting, issue analysis, follow-up, escalation briefs)

- **Conversational Copilot (`conversational_copilot_improved.py`)**
  - Interactive CLI chatbot
  - Uses `langchain + langgraph` for ReAct agent
  - Remembers tickets, orders, and customers across conversation
  - Automatically fetches policies from SQLite

---

## 🚀 Setup & Run

### 1. Clone Repo
```bash
git clone https://github.com/<your-username>/customer-support-copilot.git
cd customer-support-copilot
```
### 2. Install Dependencies
```bash
pip install -r requirements.txt
```
### 3. Configure API Key
Create a .env file:
```bash
GROQ_API_KEY=your_api_key_here
```
### 4. Start Servers
Run each server in a separate terminal:
```bash
python tools.py
python resources.py
python prompts.py
```
### 5. Start Copilot
```bash
python conversational_copilot_improved.py
```
## 📂 Project Structure
```graphql
customer-support-copilot/
│── tools.py                  # MCP Tools Server
│── resources.py              # MCP Resources Server (SQLite policies)
│── prompts.py                # MCP Prompts Server
│── conversational_copilot_improved.py  # Main conversational agent
│── policies.db               # Example SQLite database with policies
│── requirements.txt          # Python dependencies
│── README.md                 # Documentation
```

## 🛠 Future Enhancements
Add a web UI instead of CLI
  - Extend policy database
  - Integrate real CRM/ticket system
  - Add authentication for MCP servers

