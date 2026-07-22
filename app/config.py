import os 
# pyrefly: ignore [missing-import]
from dotenv import load_dotenv

load_dotenv()

class Settings:
    # ---- GCP Config ----
    PROJECT_ID = os.getenv("PROJECT_ID","enterpriserag1902")
    LOCATION = os.getenv("LOCATION","us-central1")
    GCP_DOC_AI_LOCATION = os.getenv("GCP_DOC_AI_LOCATION","us")
    GCP_DOC_AI_PROCESSOR_ID = os.getenv("GCP_DOC_AI_PROCESSOR_ID")
    RAW_BUCKET = os.getenv("GCP_RAW_BUCKET","enterpriserag1902-rag-raw")
    PROCESSED_BUCKET = os.getenv("GCP_PROCESSED_BUCKET","enterpriserag1902-rag-processed")

    # -- Vector DB (QDRANT) -- 
    QDRANT_URL = os.getenv("QDRANT_CLUSTER_ENDPOINT")
    QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
    QDRANT_COLLECTION = "enterpriserag1902"

    # -- Reasoning engine (GROQ) --
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    GROQ_MODEL = "llama-3.3-70b-versatile"
    GROQ_FALLBACK_API_KEY = os.getenv("GROQ_FALLBACK_API_KEY")

    # -- LLM GATEWAY (PORTKEY) -- 
    PORTKEY_API_KEY = os.getenv("PORTKEY_API_KEY")
    GROQ_SLUG = "rag" # primary virtual key: @rag/llama-3.3-70b-versatile
    GROQ_SLUG_2 = "brag" # fallback virtual key: @brag/llama-3.1-8b-instant



    # -- Observability ---
    LANGSMITH_TRACING = os.getenv("LANGSMITH_TRACING","true")
    LANGSMITH_API_KEY = os.getenv("LANGSMITH_API_KEY")
    LANGSMITH_PROJECT = os.getenv("LANGSMITH_PROJECT","")
    LANGSMITH_ENDPOINT = os.getenv("LANGSMITH_ENDPOINT", " ")

    # Apply Langchain environment variables for automatic tracing
    os.environ["LANGCHAIN_TRACING_V2"] = os.getenv("LANGSMITH_TRACING", "true")
    os.environ["LANGCHAIN_API_KEY"] = os.getenv("LANGSMITH_API_KEY", "")
    os.environ["LANGCHAIN_PROJECT"] = os.getenv("LANGSMITH_PROJECT", "enterpriserag1902")
    os.environ["LANGCHAIN_ENDPOINT"] = os.getenv("LANGSMITH_ENDPOINT", "https://api.smith.langchain.com")

settings = Settings()

