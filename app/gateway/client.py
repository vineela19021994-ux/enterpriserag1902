import logfire
from portkey_ai import Portkey, createHeaders, PORTKEY_GATEWAY_URL
from langchain_openai import ChatOpenAI


# "If Portkey SDK already works, why use LangChain?"

# Portkey SDK and LangChain serve different purposes. The Portkey SDK is responsible for 
# communicating with the Portkey Gateway and providing gateway features like logging, 
# retries, fallback, caching, and routing. LangChain is an AI application framework that 
# provides prompt templates, chains, memory, agents, tools, and LangGraph integration. 
# In production, we often use LangChain to build the application logic and Portkey to 
# manage and observe all LLM requests.

from app.config import settings # This will import the settings class so that we can hit the 
                                #    configuration variables

# In our scenario the best possible gateway would be semantic cache, model fall back [if one groq
#         model is failing we will fallback to the second model]
#     These both concepts we will be integrating as our gateways in our system

# Production gateway config:
#   - Fallback: primary @rag/llama-3.3-70b-versatile → @brag/llama-3.1-8b-instant on failure
#   - Cache: semantic mode (requires Portkey Enterprise — silently falls back to simple on free/starter)
#   - Retry: 2 attempts on rate limit / server error before triggering the fallback target


GATEWAY_CONFIG = {
    "strategy": {"mode": "fallback"},
    "cache": {"mode": "simple"},
    "retry": {
        "attempts": 2,
        "on_status_codes": [429, 503]
    },
    "targets": [
        {"override_params": {"model": f"@{settings.GROQ_SLUG}/llama-3.3-70b-versatile"}},
        {"override_params": {"model": f"@{settings.GROQ_SLUG_2}/llama-3.1-8b-instant"}},
    ]
}

# 1) It tells portkey : 
#    Whenever a request comes to me , follow these rules before sending it to the AI model 

#    This is a Portkey Gateway configuration. It tells Portkey to first check the cache 
#    for an existing response. If no cached response is found, it sends the request to 
#    the primary model. If the model returns temporary errors like 429 or 503, 
#    Portkey retries the request up to two times. If the primary model still fails, 
#    Portkey automatically switches to the backup model using the fallback strategy.

#     Cache → Reuse old answer.
#     Retry → Try the same model again.
#     Fallback → Use another model if the first one fails.
#     Targets → List of models Portkey can use.

portkey_client = Portkey(
    api_key=settings.PORTKEY_API_KEY,
    config=GATEWAY_CONFIG
)

# This code creates a Portkey client and attaches the GATEWAY_CONFIG to it. From this 
# point onward, every request sent through portkey_client automatically follows the 
# configured gateway rules such as caching, retries, fallback, and model routing 
# without requiring additional logic in the application.

def get_langchain_llm(feature: str = "rag") -> ChatOpenAI:
    """
    Returns a Portkey-backed ChatOpenAI — a drop-in for ChatGroq in LangChain nodes.

    Why ChatOpenAI and not ChatGroq:
      Portkey is a proxy. It exposes an OpenAI-compatible endpoint at PORTKEY_GATEWAY_URL.
      ChatGroq is hardwired to Groq's API and does not support routing through a proxy.
      ChatOpenAI supports base_url (points at Portkey) and default_headers (passes Portkey
      auth + config). The @rag/model-name format is Portkey-specific — Groq's own client
      does not understand it. You are still using Groq models; Portkey is just in the middle.
    """
    return ChatOpenAI(
        api_key=settings.PORTKEY_API_KEY,
        base_url=PORTKEY_GATEWAY_URL,
        model=f"@{settings.GROQ_SLUG}/llama-3.3-70b-versatile",
        temperature=0,
        default_headers=createHeaders(
            api_key=settings.PORTKEY_API_KEY,
            config=GATEWAY_CONFIG,
            metadata={
                "feature": feature,
                "_user": "rag-system",
                "environment": "production"
            }
        )
    )

    # This function creates a LangChain ChatOpenAI object that routes all LLM requests 
    # through the Portkey Gateway. The base_url points to Portkey, the model tells 
    # Portkey which Groq model to use, createHeaders() adds Portkey authentication, 
    # gateway configuration, and metadata, and temperature=0 ensures deterministic 
    # responses. This allows us to use LangChain features while benefiting from Portkey 
    # features like caching, retries, fallback, logging, and routing.


def extract_cache_status(response) -> str:
    """
    Pull x-portkey-cache-status from the Portkey native client response headers.
    Tries multiple attribute paths defensively — returns 'MISS' if not found.
    """
    for attr in ("_raw_response", "_response", "_http_response"):
        raw = getattr(response, attr, None)
        if raw is not None:
            status = getattr(raw, "headers", {}).get("x-portkey-cache-status", "")
            if status:
                return status.upper()
    return "MISS"


# 1) Check whether the answer came from the Portkey cache or from the AI model
#    This creates a function that takes a response and returns a string . 
#    Example return values : HIT , MISS

#    When portkey sends a response , it includes a special header like below 
#    x-portkey-cache-status : HIT
#    or 
#    x-portkey-cache-status : MISS

#    Meaning:
#     HIT → Answer came from the cache.
#     MISS → Portkey called the AI model.

#     "x-portkey-cache-status : HIT" => The x-portkey-cache-status header is added 
#     automatically by the Portkey Gateway. When caching is enabled in the gateway 
#     configuration, Portkey checks the cache for each request and includes a 
#     header such as HIT or MISS in the response. The application only reads this 
#     header; it does not create it.

# 2) extract_cache_status() checks the Portkey response headers to determine whether 
#    the response came from the cache or from a fresh LLM call. It looks for the 
#    x-portkey-cache-status header, returns HIT or MISS, and defaults to MISS if 
#    the header is not found."