import logfire # To log everything 
from langchain_groq import ChatGroq
from nemoguardrails import RailsConfig, LLMRails

from app.config import settings
from app.guardrails.colang_rules import COLANG_CONTENT, YAML_CONTENT, RAIL_INDICATORS


_rails: LLMRails | None = None


def initialize_rails() -> None:
    """
    Build the NeMo LLMRails singleton at app startup.
    Uses llama-3.1-8b-instant for fast intent classification at the gate —
    the heavier llama-3.3-70b-versatile is reserved for the RAG pipeline.
    """
    global _rails

    # This LLM is used to detect the user intent 
    guard_llm = ChatGroq(
        api_key=settings.GROQ_API_KEY,
        model="llama-3.1-8b-instant",
        temperature=0
    )
     
    # setting up the configuration 
    config = RailsConfig.from_content(
        colang_content=COLANG_CONTENT,
        yaml_content=YAML_CONTENT
    )
     
    # creating the rails object and logging in logfire
    _rails = LLMRails(config, llm=guard_llm)
    logfire.info("🛡️ NeMo Guardrails initialised (llama-3.1-8b-instant).")
    
    

# This guard function is going to take user message as input and it will return a tuple which is a 
#    boolean value ie True or False 
#    True if a rail is fired , which means if the user has said something wrong  that is when 
#        the guard will be triggered 
#    False if the user has said nothing wrong ie the message is clean and the guard will not be triggered  
def guard(message: str) -> tuple[bool, str | None]:
    """
    Run a user message through the NeMo rails gate.

    Returns:
        (True,  rail_response) — a rail fired; return this response immediately,
                                skip the RAG pipeline entirely.
        (False, None)          — message is clean; proceed to LangGraph.
    """
    if _rails is None:
        logfire.warning("⚠️ Guardrails not initialised — skipping gate.")
        return False, None

    with logfire.span("🛡️ Guardrails Check"):
        result = _rails.generate(messages=[{"role": "user", "content": message}])

        # NeMo returns {'role': 'assistant', 'content': '...'} — extract text
        content = result.get("content", "") if isinstance(result, dict) else str(result)

        fired = any(indicator in content for indicator in RAIL_INDICATORS)

        if fired:
            logfire.info(f"🛡️ Guardrails fired | query='{message[:80]}'")
            return True, content

        logfire.info("✅ Guardrails passed.")
        return False, None

# 1) Railsconfig is used to load the nemo guardrails configuration including the colang flows ,
#    yaml configuration and model settings . 
#    Once the configuration is loaded we create an LLMRails object . 

# 2) LLMRails is responsible for executing those guardrails .
#    Whenever a user sends a query, it checks whether any guardrail, such as a greeting, 
#    off-topic, or jailbreak protection, is triggered and returns the appropriate 
#    response before the request proceeds further.

# 3) initialize_rails()  => used in main.py 

# 4) Guard function : 
#    This function acts as the entry point to the application . Every user query first passes through 
#    nemo guardrails  . 

#    Guardrails returns a response based on Configured colang flows. We then compare the response 
#    with our rail_indicators ist using python any() function .

#    If any indicator matches any() returns True so fired becomes true  and we immediately return the 
#    guardrails response without executing the rag pipeline .
#    If none of the indicators match  fired becomes false and the request continues to langgraph 
#    workflow 

