from fastapi.middleware.asyncexitstack import AsyncExitStackMiddleware
import logfire 
from langchain_groq import ChatGroq 
from app.agents.state import AgentState 
from app.config import Settings 

# Initialize the Groq model 
llm = ChatGroq(
    api_key = Settings.GROQ_API_KEY,
    model = Settings.GROQ_MODEL,
    temperature=0.1
)


def generate_node(state:AgentState):
    """
    Synthesizes a responses  using  both Documentation  Context and Conversation History
    """
    query = state["current_query"]

    # Format the entire history for the LLM 
    history_str = ""
    for msg in state["messages"][:-1]:
        role = "User" if msg["role"] == "user" else "Assistant"
        history_str += f"{role}: {msg['content']}\n"

    user_msg = state["messages"][-1]["content"] if state["messages"] else ""

    if query == "CONVERSATIONAL":
        logfire.info("Generating conversational response using memory.")
        prompt = f"""
        You are a friendly and helpful Enterprise AI assistant.
        Answer the user's latest message using the CONVERSATION HISTORY  below.

        CONVERSATION HISTORY:
        {history_str}

        LATEST_MESSAGE:
        "{user_msg}"

        """
    else : 
        # Technical RAG Logic with Token Safety 
        logfire.info("Generating technical RAG response.")
        max_context_chars = 25000
        full_context = ""
        
        for doc in state["documents"]:
            if len(full_context)+len(doc) < max_context_chars:
                full_context += doc + "\n\n"
            else : 
                logfire.warning("Context truncated to fit  Groq TPM limits")
                break

        prompt = f"""
        You are a Senior Technical Architect.
        Answer the question using the TECHNICAL CONTEXT provided.

        TECHNICAL CONTEXT:
        {full_context}

        CONVERSATION HISTORY:
        {history_str}

        USER QUESTION:
        "{user_msg}"
        """

    with logfire.span("✍️ LLM Synthesis"):
        try : 
            response = llm.invoke(prompt)
            logfire.info("Response synthesized successfully")
            return {
                "final_answer" : response.content,
                "status" : "Response generated.",
                "messages" : [{"role": "assistant","content": response.content}]
            }

        except Exception as e: 
            logfire.error(f"LLM Generation failed:{e}")
            raise e


# 1) This is the final response generation node in agentic RAG system 
#    Its job is : 
#    generate final answer 
#    use conversation history 
#    optionally use retrieved documents 
#    call the LLM 
#    return assistant response 

# 2) This function handles two scenarios : 
#    Conversational Query => answer using memory/history 
#    Technical Query => answer using RAG documents+history 

# 3) This node recevies : shared agent state 
#    Gets planner decision ie either "conversational" or "user query"
#    Processes all previous messages except latest one
#    Taking all the previous conversations and user query 

#    If it is "conversational" , no retrieval needed 
#    Use only memory and conversational history 

#    If it is "technical" ,technical retrieval required
#    max_context_chars = 25000 => This line sets the maximum amount of document context that can be 
#                                 sent to the LLM 
#                                 Because models have limits on input size , tokens/context length
#        process retrieved chunks => They are retrieved earlier from Qdrant during retrieval stage 
#                                    and stored in state["documents"] in retriever.py 
#                                    The generate_node() function simply consumes those retrived chunks 

#        Add chunks to final_context 
#        Protects LLM call from overflow 
#        Builds RAG prompt 
#        Sends prompt to LLM 
#        Returns => generated answer , updated status , assistant message

