from langchain_core.utils import strings
from typing import TypedDict,List,Annotated
import operator 

class AgentState(TypedDict):
    # Using Annotated with operator .add ensures that messages
    # are appended to the history rather than replaced
    messages:Annotated[List[dict],operator.add]
    current_query : str
    documents : List[str]
    plan : List[str]
    status : str 
    final_answer : str


# 1) The state.py file is basically used to define the shared memory structure for the AI agent/
#    workflow 
#    It defines what information the agent can store and pass between different workflow steps 
#    It RAG, multiple steps happen , all these steps need shared data 

# 2) Agent workflows often contain :
#    multiple nodes , branching logic , iterative reasoning 
#    State helps : maintain continuity , share data between nodes , track progress

# 3) Typed Dict : used to define structured dictionary schema 
#    List : list of strings
#    Annotated : Adds extra metadata/behaviour to type 

# 4) messages : When new message comes, APPEND them instead of replacing with old messages 
#    Without this , old conversation history may disappear
#    We need this for : conversation memory , history tracking , multi step reasoning
#    This will be a list of dictionary 

# 5) current query : Stores current user query 

# 6) documents : Stores retrieved documents/chunks

# 7) plan : Stores agent execution plan/steps 
#    In agentic workflows , agents often think step by step 

# 8) status : Stores current flow status

# 9) final answer : Stores final generated response