from langchain_groq import ChatGroq
from app.agents.state import AgentState 
from app.config import Settings 
import logfire 

# Initialize the Groq model 
llm = ChatGroq(
    api_key = Settings.GROQ_API_KEY,
    model = Settings.GROQ_MODEL,
    temperature = 0 
)


def planner_node(state : AgentState):
    """
    The planner determines if a search is needed based on the ENTIRE Conversation
    """

    # Get the conversation history (excluding the last message)
    history = ""
    for msg in state["messages"][:-1]:
        role = "User" if msg["role"] == "user" else "Assistant"
        history += f"{role} : {msg['content']}\n"

    user_message = state["messages"][-1]["content"] if state["messages"] else ""

    prompt = f"""
    You are an intelligent Assistant Planner.
    Analyze the conversation history and the latest user message.

    CONVERSATION HISTORY:
    {history}

    LATEST MESSSAGE:
    "{user_message}"

    Task :
    1. If the latest message is a greeting (hi,hello) or a question that can be answered using ONLY
       the conversation history above (e.g., "what is my name"), respond  with 'CONVERSATIONAL'.

    2. If it is a  technical  question about kubernetes, Intel or Networking that requires fresh documentation 
       output a refined search query.

    Output ONLY "CONVERSATIONAL" or the search query.
    """

    with logfire.span("🧠 Planner Decision"):
        decision = llm.invoke(prompt).content.strip()
        logfire.info(f"Intent identified: {decision}") 
    
    if decision == "CONVERSATIONAL":
        return{
            "current_query":"CONVERSATIONAL",
            "status":"Handling conversationally (using memory)...",
            "plan":["Intent:Conversational/Memory","Retrieval:Skipped"]
        }

    return{
        'current_query': decision,
        'status':f"Technical research needed.Searching for:{decision}",
        "plan":["Intent : Technical",f"Search Term:{decision}"]
    }


# 1) This code creates a planner agent node in your agentic RAG system.
#    Its job is to decide :
#    whether retrieval search is needed 
#       OR 
#    whether the response can be answered conversationally using memory/history

# 2) Agent state is imported so every agent node follows the same shared memory structure while 
#    processing the workflow.
#    It ensures that the defined information is consistently stored and passed between different stages 
#    of the agentic RAG pipelines.

# 3) planner_node : 
#    This node receives : current agent state as the input

#    decides : conversational responses? [or] retrieval required?
#    Creates an empty history string 

#    Loops through old messages => Processes all messages except the last one 
#    Why exclude last message ? Because it is the current user query .
#    The latest message is separated from the conversation history so the planner can clearly distinguish 
#    between prior context and the current user request. This avoids duplicating the latest query 
#    inside the prompt and improves prompt clarity for the LLM . 
#    state["messages"] => contains full chat history 

#    This code separates previous conversation history from the latest user query . It formats 
#    old messages into a readable history string while extracting the most recent message separately
#    so the planner LLM can clearly distinguish between prior context and the current request.

# 4) This prompt instructs the planner LLM to analyze conversation history and the latest user message 
#    to determine whether the request can be answered conversationally from memory or requires 
#    technical document retrieval . It also contraints the output format so downstream workflow routing 
#    remains predictable and structured.

# 5) decision : Groq model , sends prompt to the LLM 
#               LLM returns either "conversational" or "user query"
#    .content : LLM response object contains metadata , content 
#               .content extracts only text response 

# 6) If decision is "conversational" , Planner decided no retrieval needed . This can be answered 
#    using memory/history only
#    Returns updated agent state.

#    Returned data : 
#    current_query => no technical search query needed 
#    Status => Indicates use conversation memory only 
#    plan => shows workflow decision 

# 7) For else condition : 
#    If "not conversational" , planner decided technical retrieval required 
#    Stores refined search query 
#    Indicates retrieval pipeline should start 