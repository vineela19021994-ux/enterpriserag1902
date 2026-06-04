import logfire  # To log our agents
from app.agents.state import AgentState  # To maintain the agent context
from app.services.retrieval.qdrant_service import search_enterprise_knowledge # To fetch data from qdrant
from app.services.retrieval.ranking_service import rerank_documents # To re-rank the documents
# Flashrank for re-ranking

def retrieve_node(state : AgentState): # We are taking agent state as the input here 
    """
    Performs vector search and semantic reranking for technical queries.
    """
    query = state["current_query"] # This is the query that the planner node has refined 
    # and is sending to the retrieve node

    # Standard Retrieval Logic 
    with logfire.span("🔍 Knowledge Retrieval"): 
        logfire.info(f"Searching Qdrant for: {query}")
        raw_results = search_enterprise_knowledge(query, limit = 15)
        logfire.info(f"Retrieved {len(raw_results)} candidates from vector DB")

        doc_contents = [doc['content'] for doc in raw_results]
        # Raw results are the results directly from qdrant

        with logfire.span("⚖️ Semantic Reranking"):
            reranked_contents= rerank_documents(query,doc_contents,top_n= 5)
            logfire.info("Reranking complete.Kept top 5 most relevant chunks.")

        formatted_docs = [f"CONTENT:{doc}" for doc in reranked_contents]
        #Formatted docs are the final top 5 documents that are retrieved 

    return{
        "documents" : formatted_docs,
        "status" : f"Found technical context,",
        "plan" : state["plan"] + ["Context Retrieved"] # To update the agent state
    }


# 1) This node is the **retrieval engine** of your RAG agent.
#     Its job is to fetch relevant documents from your knowledge base
#     based on the planner's query.

# 2) It uses **vector search** (Qdrant) + **semantic re-ranking** (Flashrank)
#    to ensure the most relevant context is retrieved, not just keyword matches.

# 3) Input **query** comes from `planner_node` (either user query or refined search term)

# 4) **Vector Search (Qdrant)**:
#    - `search_enterprise_knowledge()` performs dense vector search using embeddings
#    - It returns top 15 candidate chunks (more than needed so we have options)

# 5) **Document Formatting**: 
#    - Extract only `content` from Qdrant results
#    - Clean and prepare for re-ranking

# 6) **Semantic Re-ranking (Flashrank)**:
#    - Takes the raw candidate chunks + original query
#    - Uses compact ONNX cross-encoder (efficient & accurate)
#    - Returns top 5 **most relevant** chunks
#    - *Why re-rank?* Vector search retrieves similar items, but re-ranker checks **true semantic relevance**

# 7) **Final Output**: 
#    - Returns updated state with:
#      - `documents`: Top 5 ranked chunks (formatted as `CONTENT:...`)
#      - `status`: Updated status message
#      - `plan`: Adds "Context Retrieved" step