
from typing import List
# pyrefly: ignore [missing-import]
import logfire

def chunk_text(text:str, chunk_size : int = 1500) -> List[str]:
    """
    Simple semantic-ish chunker that splits by paragraph
    Ensures chunks do not exceed the specified size
    """

    with logfire.span("✂️ Text Chunking", text_length= len(text)):
        if not text.strip():
            return []

        paragraphs = text.split("\n\n")
        chunks = []
        current_chunk = ""
        
        for p in paragraphs:
            if len(current_chunk) + len(p) < chunk_size:
                current_chunk += p + "\n\n"
            else :
                if current_chunk.strip():
                    chunks.append(current_chunk.strip())
                current_chunk = p + "\n\n"
        
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        valid_chunks = [c for c in chunks if c.strip()]
        logfire.info(f"✅ Generated {len(valid_chunks)} chunks")
        return valid_chunks

# 1) Chunking is important because :
#    LLMs have token limits
#    embeddings work better on smaller text
#    retrieval becomes more accurate
# 2) We are using function "chunk_text"
#    Initially we will take all the text and separate by paragraphs
#    For each paragraph we will check the length and we will append it to the chunk
# 3) If the current chunk is full , save it and start a new chunk with the current paragraph