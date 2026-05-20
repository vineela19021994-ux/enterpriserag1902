# pyrefly: ignore [missing-import]
from sys import UnraisableHookArgs
from _winapi import STARTF_FORCEONFEEDBACK
# pyrefly: ignore [missing-import]
import vertexai # used for embeddings , embeddings are generated using vertex AI models
# pyrefly: ignore [missing-import]
from vertexai.language_models import TextEmbeddingModel
from app.config import Settings

model = None # Initially no model is loaded
BATCH_SIZE = 50 # Defines how many text chunks are processed together during embeddings


def get_embedding_model():
    global model # function uses global model variable defined outside
    if model is None:
        # Initialize vertex ai before loading the model
        vertexai.init(project = Settings.PROJECT_ID,location = Settings.LOCATION)
        # Reverting to TextEmbeddingModel for stability
        model = TextEmbeddingModel.from_pretrained("text-embedding-004")
    return model
    

def embed_query(query:str):
    """
    Embeds a single query string using the stable vertex AI API
    """
    model = get_embedding_model()
    embeddings = model.get_embeddings([query])
    return embeddings[0].values

def embed_texts(texts:list[str]):
    """
    Embeds a list of strings in batches
    """
    model = get_embedding_model()
    all_embeddings = []

    for i in range(0,len(texts),BATCH_SIZE):
        batch = texts[i:i+BATCH_SIZE]
        embeddings = model.get_embeddings(batch)
        all_embeddings.extend([e.values for e in embeddings])
    
    return all_embeddings



# vertexai.init(project = Settings.PROJECT_ID,location = Settings.LOCATION)
#   Initializes vertex ai Sdk 
#   This connects the application to GCP project, region/location
#   After connecting to vertex ai , we are specifying "text-embedding-004" model to use as vertex
#   ai will have soo many models

# "embed_texts" :
# Extract batch of text chunks from the full text list so embeddings can be generated efficiently 
# in smaller groups instead of processing all texts at once.
# This improves :
#        performance
#        memory usage 

