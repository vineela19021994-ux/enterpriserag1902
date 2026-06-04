from sqlalchemy.util import MemoizedSlots
from langgraph.graph import StateGraph,END
from langgraph.checkpoint.memory import MemorySaver
# We are using the memory saver so that we can maintain the chat history of the user 
# Later on we will replace this memory saver with postgreSQL so maintain all the history in the cloud
#    because once the container is crashed or restarted this memory is lost . 
#    We want to retain this memory over time 
from app.agents.state import AgentState 
from app.agents.nodes.planner import planner_node 
from app.agents.nodes.retriever import retrieve_node 
from app.agents.nodes.responder import generate_node

# 1.Initialize the State Graph 
workflow = StateGraph(AgentState)

# 2.Define the nodes
workflow.add_node("planner",planner_node)
workflow.add_node("retriever",retrieve_node)
workflow.add_node("responder",generate_node)

# 3. Define the edges and routing logic "rounting function"
#    This takes the agent state
def route_planner(state:AgentState):
    """
    Routes the workflow based on the planners decision
    """
    if state["current_query"] == "CONVERSATIONAL":
        return "responder"
    return "retriever"

    # If the state of the current query is conversational it is directly going to return the 
    # responder if not it is going to return the retriever

workflow.set_entry_point("planner") # Entry point is always the planner node 

# Conditional Egde : Planner -> Router -> (Retriever OR Responder)
workflow.add_conditional_edges(
    "planner",
    route_planner,
    {
        "retriever" : "retriever",
        "responder" : "responder"
    }
)

# For the conditional edge where it starts with the planner , 
# it can go to the retriever or the responder   

# sequential edges after retriever the only way is to go to the responder 
workflow.add_edge("retriever","responder")
workflow.add_edge("responder",END)

# -- MEMORY UPGRADE ---
# MemorySaver allows the agent to remember conversations based on "thread_id"
checkpointer = MemorySaver()

# 4. Com pile the Graph with Memory 
rag_agent = workflow.compile(checkpointer = checkpointer)


# 1) In langraph we have nodes and edges  
#    3 nodes : Planner , Responder , Retriever 
#    2 edges : Conditional edge , Sequential edge 

