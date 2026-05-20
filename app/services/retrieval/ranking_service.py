from time import time
from _winapi import NeedCurrentDirectoryForExePath
import time
# pyrefly: ignore [missing-import]
import logfire
# pyrefly: ignore [missing-import]
from flashrank import Ranker,RerankRequest

# Lazy initialization - Ranker is loaded on first use to ensure logfire.configure() has run
_ranker = None

def _get_ranker() -> Ranker:
    """
    Initializes the FlashRank engine lazily.
    FlashRank uses a local ONNX model (ms-marco-MiniLM-L-6-v2) for ultra fast re-ranking
    """

    global _ranker
    if _ranker is None:
        logfire.info("🧠 Initializing FlashRank Model (TinyBERT) locally...")
        try:
            # We use a specific cache directory to avoid permission issues in production
            _ranker = Ranker(cache_dir = "/tmp/flashrank")
        except Exception:
            _ranker = Ranker()
    return _ranker
    # Here we didnt mention any reranking model 
    # Flashrank automatically loads the default reranking model internally or another 
    #   compact ONNX reranker depending on the flashrank version


    def rerank_documents(query : str , documents : list[str], top_n : int = 5) -> list[str]:
        """
        Refines retrieval results by re-scoring documents against the query semantically

        Why Flash Rank?
        Standard vector search (cosine similarity) is fast but mathematically fuzzy.
        FlashRanker uses a cross-encoder approach which is much more precise but usually slow
        Flash rank solves this by using highly optimized, quantized ONNX models locaaly 
        """

        if not documents:
            return []
        
        start_time= time.time()
        logfire.info(f"📡 [Reranker] Sending {len(documents)} docs to FlashRank Cross-Encoder...")

        try:
            ranker = _get_ranker()

            # Flashrank expects a list of dictionaries with 'id' and 'text'
            passages = [
                {"id": i,"text": doc}
                for i,doc in enumerate(documents)
            ]

            request = RerankRequest(query = query , passages = passages)
            results = ranker.rerank(request)

            # Results are returned sorted by highest semantic score first
            reranked_docs = []
            for res in results[:top_n]:
                reranked_docs.append(res['text'])
            
            duration = time.time() - start_time
            top_score = results[0]['score'] if results else 'N/A'
            logfire.info(f"✅ [Reranker] Done in {duration:.2f}s. Top semantic score: {top_score}")

            return reranked_docs
    
        except Exception as e:
            logfire.error(f"❌ [Reranker] Semantic Reranking Failed: {e}")
        # Fallback to the original Qdrant order to ensure the user still gets an answer
            return documents[:top_n]


# 1) A Cross Encoder is a reranking model architecture that evaluates query-document relevance 
#    together, while FlashRank is a lightweight reranking library/framework optimized for 
#    fast and efficient reranking, often using compact cross encoder models internally.

# 2) _get_ranker :
#    Initially no flash rank model is loaded
#    _get_ranker => used to load the flashrank model and return reranker object
#    Lazy initialization : load only when needed 
#    global _ranker : allows function to modify global _ranker, prevents creation of local variable 
#    checks if flash rank model is already loaded
#    Logs model loading activity
#    Loads flash rank reranker model , uses local cache directory to store the model related cache files
#       ONNX model files ,tokenizer files , model configs , cached model assests are stored
#    With cache :
#       reuse existing files 
#       faster startup 
#       lower latency
#    if cache directory fails , initialize normally 
#    returns flashrank reranker object 
   
# 3) rerank_documents :
#    Track re-ranking latency using the start time
#    Flash rank expect structured format :
#         So we take the id and chunk
#    Create a re-ranking request 
#    Run re-ranking  where Flash rank compares query against each chunk , calculate semantic 
#         relevance score , sort chunks by relevance
#    After re-ranking take top n results 
#    Measure total time 
#    top_score = results[0]['score'] => Gets best semantic score
#    Log completion : reranking completed , duration , best score

   