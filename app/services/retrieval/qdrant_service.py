# pyrefly: ignore [missing-import]
import logfire # logging/observability library
# pyrefly: ignore [missing-import]
from qdrant_client import QdrantClient # for storing embeddings
# pyrefly: ignore [missing-import]
from qdrant_client.http import models # import Qdrant data models
from app.config import Settings
from app.services.retrieval.embedding import get_embedding_model,embed_query

# Initialize Qdrant client
# Connect to the Qdrant vector database using this URL and API key
client = QdrantClient(
    url = Settings.QDRANT_URL,
    api_key = Settings.QDRANT_API_KEY
)

def search_enterprise_knowledge(query : str,limit : int = 8):
    """
    Performs a high precision search in the enterprise knowledge base
    Uses the modern query points interface
    """
    try : 
        query_vector = embed_query(query)

        # Using query points - the modern standard for Qdrant
        response = client.query_points(
            collection_name = Settings.QDRANT_COLLECTION,
            query = query_vector,
            limit = limit,
            with_payload = True # JSON
        )

        results = []
        for res in response.points:
            results.append({
                "content":res.payload.get("text",""),
                "source":res.payload.get("source","Unknown"),
                "score":res.score
            })

        return results

    except Exception as e :
        logfire.error(f"❌ Qdrant Search Failed: {e}")
        return []



# 1) from qdrant_client.http import models 
#    These models are used to define how data should be stored and searched inside the 
#    vector database Qdrant
#    vector point objects => used for storing embeddings
#    Query structures => used for searching

# 2) from qdrant_client import QdrantClient
#    imports the Qdrant database client into python application

# 3) In search_enterprise_knowledge:
#    User query gets converted into vector
#    Then searches the Qdrant using "query_points" command 
#    Qdrant collection : which vector collection to search 
#    query_vector : embedding vector for user query 
#    limit : How many results to return 
#    with payload : metadata stored with vectors 

#    Then format results :
#    results.append : We add retrieved chunk text with source filename/document
#                     and also similarity score

