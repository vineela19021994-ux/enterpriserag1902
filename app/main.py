# ============================================================
# CRITICAL: logfire MUST be configured before ALL other imports
# so that spans from all modules are captured from the start.
# ============================================================


from mysql.connector.connection_cext import exc
import logfire 
import os 
from dotenv import load_dotenv

load_dotenv()
logfire.configure(token = os.getenv("LOGFIRE_TOKEN"))

# Now safe to import app modules - logfire is already active

# Used to create fastapi applications, response : controls what is sent back to the client 
# Response can be used when you want to customize the HTTP response returned by the API
from fastapi import FastAPI,Response
from app.agents.graph import rag_agent
# This imports Basemodel from pydantic library 
# Basemodels is used to create data models that automatically : validate data types , Parse input data ,
#      convert data into python objects , Generate structured JSON responses
from pydantic import BaseModel
from typing import Optional 

# Initialize FastAPI application
app = FastAPI(title = "Enterprise Agentic RAG API")


# Pydantic model used to define the structure of incoming API request. 
# Query Request should be validated with the pydantic base model 
# q => User's query (string)
# thread_id => Unique identifier for conversation memory (optional, default = "default_user") 
# thread_id is used to maintain conversation history for each user
# thread_id will be passed to the checkpointer and memory saver in graph.py and this is how the chat history will be maintained
class QueryRequest(BaseModel):
    q : str  
    thread_id : Optional[str] = "default_user"

# When we hit / we should get this response ie the Home page
@app.get("/")
def home():
    return {"message": "Enterprise Langgraph RAG API is live"}

# We made the rag_agent graph , if we want to visualize this graph we are making route for this
# When we hit /graph it will return the mermaid image of the agentic workflow
@app.get("/graph")
def get_graph_image():
    """
    Returns the Mermaid image of the agents workflow
    """
    try:
        png_bytes = rag_agent.get_graph().draw_mermaid_png()
        return Response(content = png_bytes , media_type="image/png")
    except Exception as e :
        return {"error":f"Could not generate graphimage: {e}"}

# Query Route : 
# This is a post request because we are sending the query to the application API for requesting a response
#   and it will be in the form of validated  query request 
@app.post("/query")
def query(request : QueryRequest):
    """
    Executes the Langgraph RAG flow with memory using a POST request
    """
    # It is requesting the response for this particular query and thread.id
    q = request.q
    thread_id = request.thread_id

    # This is the initial state when the graph is starting
    # Here we are maintaining a flow 
    initial_state = { 
        "messages" : [{"role":"user","content":q}],
        "current_query":q,
        "documents":[],
        "plan":["Start"],
        "status":"Initializing graph..."
    }

    # Configuration for Memory (Thread ID), to maintain conversational memory
    # We are using configurable to configure the thread id 
    config = {"configurable":{"thread_id":thread_id}}

    try:
        # Run the graph synchronously to perserve  Logfire context variables 

        # Final output is going to be given by rag_agent invoking which is going to input the
        #    initial state and it is going to update it over time and the configuration 
        # Graph is taking two things in the end , rag_agent will be invoked and the checkpointer needs
        #    a thread, the thread is put in a configurable which we are passing with the rag_agent 
        final_output = rag_agent.invoke(initial_state,config = config)
        
        # Returns this response ie rag_agent is going to return this response
        return { 
            "question":q,
            "answer":final_output.get("final_answer"),
            "thought_process" : final_output.get("plan"),
            "status": final_output.get("status"),
            "sources":final_output.get("documents",[])
        }
    
    except Exception as e:
        logfire.error(f"❌ Backend Execution Failed: {e}")
        return {
            "question":q,
            "answer":"I apologize, but I encountered an internal error while processing your request",
            "thought_process":["Error encountered during execution"],
            "status":"error",
            "sources":[]
        }


