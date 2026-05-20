import os
import sys
import uuid # universal unique identifier, to uniquely identify the chunks
import json # to convert all the data from different sources into json format, passed using json parser
# pyrefly: ignore [missing-import]
import logfire
# pyrefly: ignore [missing-import]
import vertexai # for embeddings

from typing import List
# pyrefly: ignore [missing-import]
from google.cloud import storage # for storage purpose
# pyrefly: ignore [missing-import]
from qdrant_client import QdrantClient # for storage purpose
# pyrefly: ignore [missing-import]
from qdrant_client.http import models # to import the models from qdrant client to use the
                                      # qdrant client models 


# Import local modules
from app.config import Settings
# pyrefly: ignore [missing-import]
from app.services.retrieval.embedding import embed_texts
from app.ingestion.loaders.pdf import parse_pdf
from app.ingestion.loaders.html import parse_html
from app.ingestion.loaders.text import parse_text
from app.ingestion.chunking.splitter import chunk_text

# Initialize logfire with the Enterprise Ingestion Service Name
logfire.configure(service_name = "enterprise-ingestion-service")

# Initialize vertex AI for embeddings
vertexai.init(project = Settings.PROJECT_ID, location = Settings.LOCATION)

# Initialize GCS client
storage_client = storage.client(project = Settings.PROJECT_ID)

#Initialize Qdrant client
qdrant_client = QdrantClient(
    url = Settings.QDRANT_URL,
    api_key = Settings.QDRANT_API_KEY
)


def upload_to_gcs(data,bucket_name: str,destination_blob_name:str,is_json:bool = False):
    """
    Uploads a file or JSON data to GCS
    """
    with logfire.span("☁️ GCS Upload", bucket=bucket_name, blob=destination_blob_name):
        try :
            bucket = storage_client.bucket(bucket_name)
            blob = bucket.blob(destination_blob_name)
            if is_json:
                blob.upload_from_string(json.dumps(data),content_type = 'application/json')
            else :
                blob.upload_from_filename(data)
            logfire.info(f"✅ Uploaded to {bucket_name}")
        except Exception as e :
            logfire.error(f"❌ GCS Upload Failed: {e}")
            raise e



def process_file(file_path : str,filename :str,source_type:str):
    """
    Orchestrates the parsing,chunking , embedding and indexing of a single file
    """
    with logfire.span("🚀 Processing File", file=filename, source=source_type):
        try:
            # 1.Upload RAW file to GCS
            raw_gcs_path = f"{source_type}/{filename}"
            upload_to_gcs(file_path,Settings.RAW_BUCKET,raw_gcs_path)

            # 2.Extract text based on extension 
            ext = filename.lower().split('.')[-1]
            if ext == "pdf":
                full_text = parse_pdf(file_path)
            elif ext in ['html','htm']:
                full_text = parse_html(file_path)
            elif ext == "txt":
                full_text = parse_text(file_path)
            elif ext in ['docx','pptx']:
                from app.ingestion.loaders.office import parse_office
                full_text = parse_office(file_path)
            else:
                logfire.warning(f"⏩ Skipping unsupported file type: {filename}")
                return

            if not full_text or not full_text.strip():
                logfire.warning(f"⚠️ No text extracted from {filename}")
                return

            # 3. Chunk text 
            chunks = chunk_text(full_text)
            if not chunks:
                return 

            # 4. Upload processed metadata to GCS
            processed_data = {"filename":filename,"chunks":chunks,"source_type":source_type}
            processed_gcs_path = f"{source_type}/{filename}.json"
            upload_to_gcs(processed_data,Settings.PROCESSED_BUCKET,processed_gcs_path,is_json=True)

            # 5.Embed and Index in Qdrant 
            with logfire.span("🧠 Vectorizing & Indexing"):
                embeddings  = embed_texts(chunks)
                points = []
                for i,(chunk,vector) in enumerate(zip(chunks,embeddings)):
                    points.append(models.PointStruct(
                        id = str(uuid.uuid4()),
                        vector = vector,
                        payload = {
                            "text":chunk,
                            "source" : filename,
                            "source_type":source_type,
                            "raw_gcs_path" : f"gs://{Settings.RAW_BUCKET}/{raw_gcs_path}"
                        }                 
                    )
                    )
                qdrant_client.upsert(
                    collection_name = Settings.QDRANT_COLLECTION,
                    points = points
                )
                logfire.info(f"✨ Indexed {len(points)} points to Qdrant")

        except Exception as e :
            logfire.error(f"💥 Failed to process {filename}: {e}")


def run_universal_ingestion(base_dir:str,explicit_source_type : str = None, wipe : bool = False):
    """
    Automatically scans the directory
    If it has subfolders,maps them to source_types.
    If it has no subfolders,uses the explicit_source_type or infers from the folder name
    """
    with logfire.span("🌍 Universal Ingestion Started", base_directory=base_dir):
        # Handle Collection wipe
        if wipe:
            with logfire.span("🧹 Wiping Collection"):
                if qdrant_client.collection_exists(Settings.QDRANT_COLLECTION):
                    qdrant_client.delete_collection(Settings.QDRANT_COLLECTION)
                    logfire.info(f"🗑️ Collection {Settings.QDRANT_COLLECTION} deleted")
                    
        # Ensure Collection Exists
        if not qdrant_client.collection_exists(Settings.QDRANT_COLLECTION):
            qdrant_client.create_collection(
                collection_name = Settings.QDRANT_COLLECTION,
                vectors_config = models.VectorParams(size = 768,distance = models.Distance.COSINE)
            )
            logfire.info(f"🆕 Created collection {Settings.QDRANT_COLLECTION}")

        # Scan for subfolders
        subdirs = [d for d in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir,d))]

        if not subdirs:
            # if no subdirs,use explicit type or infer from the base directory name 
            if explicit_source_type:
                source_type = explicit_source_type
            else :
                base_name = os.path.basename(os.path.normpath(base_dir)).lower()
                source_type = "true" if "true" in base_name else "noisy" if "noisy" in base_name else "general"

            logfire.info(f"📂 No subdirectories found, processing {base_dir} as '{source_type}'")
            process_directory(base_dir,source_type)
        else :
            for subdir in subdirs:
                source_type = "true" if "true" in subdir.lower() else "noisy" if "noisy" in subdir.lower() else subdir
                dir_path = os.path.join(base_dir,subdir)
                process_directory(dir_path,source_type)



def process_directory(dir_path: str,source_type:str):
    """
    Processes all files in a specific directory
    """
    with logfire.span("📁 Scanning Directory", path=dir_path, source=source_type):
        files = [f for f in os.listdir(dir_path) if os.path.isfile(os.path.join(dir_path,f))]
        logfire.info(f"🔍 Found {len(files)} files")

        for filename in files:
            file_path = os.path.join(dir_path,filename)
            process_file(file_path,filename,source_type)


if __name__ == "__main__":
    # Usage : python -m app.ingestion.processor [dir_path] [source_type] [--wipe]
    wipe_requested = "--wipe" in sys.argv
    clean_args = [a for a in sys.argv if a!="--wipe"]

    # Default to DATA/ if no path provided 
    target_dir = clean_args[1] if len(clean_args)>1 else "DATA"
    explicit_type = clean_args[2] if len(clean_args)>2 else None

    if not os.path.exists(target_dir):
        print(f"Error: Path {target_dir} does not exist.")
        sys.exit(1)

    run_universal_ingestion(target_dir,explicit_source_type = explicit_type, wipe = wipe_requested)
    logfire.info("🏁 Universal Ingestion Job Completed")


            





# 1) Data is coming from different source and converted into JSON ir processed data
#    This processed data is converted into embeddings using "veretx ai"
#    After embeddings we are using Qdrant to store the data
#    Raw data and processed data => stored in GCS(Google Cloud Storage)
#    For all of this we have initialized VERTEX ai , GCS and Qdrant 

# 2) upload_to_gcs : 
#    This function uploads files or JSON data to GCS
#    data : file path or the JSON data 
#    bucket_name : GCS bucket name 
#    destination_blob_name : file name/path inside GCS 
#    is_json : whether data is json 

#    bucket(cloud storage container/folder) => Connects to specific GCS bucket 
#    blob => create a file inside the bucket
#    In GCS files are called as blobs 

#    is_json = True => indicates that the input is structured python data intended to be stored as 
#                      json 
#        python objects : chunk data ,processed metadata , embedding results, retrieval results
#        These objects must be serialized into JSON before storing them in GCS
#        Since the cloud storage uploads strings or files, json.dumps() is used to serialize
#        the python object into a valid JSON string before uploading 
#     The "else" block uploads actual physical files such as PDFs,DOCX directly from the file system
#     using the file path

# 3) process_file : 
#    This is the main ingestion pipeline . It processes one document completely from start to finish.
#    Takes : file path , file name , source type 
#    Uploads the original file to GCS(Google Cloud Storage) like ex: raw PDF,raw DOCX.
#    Detect the file type , gets the extension and parse based on the file type 
#    Extract readable text from document 
#    Skip unsupported files, if unsupported files stop processing 
#    Validate Extracted text - checks whether extraction returned empty text, if empty stop processing 

#    Chunk the text : Splits large text into smaller chunks
#    Purpose => better embeddings , better retrieval 

#    Upload processed JSON to GCS : 
#    Creates processed metadata object . Contains : filename , chunks , source type
#    Stores the processed chunk data as JSON.
#    * The raw document is uploaded directly as a physical file without JSON conversion. Only the processed metadata object 
#      containing chunks and source information is converted into json using json.dumps() before being uploaded to GCS
#      json.dumps() is executed inside the upload_to_gcs() function when is_json = True is passed.

#    Generate embeddings : Converts chunks into vectors. 
#    Create Qdrant points => After generating embeddings , system must store them in Qdrant so they can later be searched during
#    retrieval 
#    The Qdrant points are the actual records stored in Qdrant , searchable vector record
#    Each point stores : ID(unique identifier), vector(embedding) ,payload (metadata/text)
#    "Why are the points created?" => Because Qdrant cannot store : plain text directly for semantic search.
#                 It stores : vectors , metadata  inside strutured points
#     "Store in Qdrant" => Using upsert , Stores all vectors into vector DB. Now chunks becomes searchable.
#     Logs success 
#     Handle errors.

# 4) run_universal_ingestion :
#    This function is the master ingestion controller of your RAG pipeline . 
#    Its job is to :
#    scan folders
#    identify document source type 
#    optionally wipe old vector data 
#    create Qdrant collection if needed 
#    process all directories/files automatically 

#    base_dir : root directory to scan 
#    explicit_source_type : manually specify the source type 
#    wipe : whether to delete existing Qdrant collection 

#    Check wipe option : If user wants fresh ingestion , old vector collection is deleted.
#    Logs collection deletion activity .
#    Checks whether vector collection already exists in Qdrant . If yes deletes old vectors completely 
#    This is useful when : rebuilding embeddings , refreshing ingestion , cleaning old data 

#    If collection does not exists , creates a new collection vector [collection = vector table/database]
#    and configure the vector settings
#    size : 768 => Embedding vector dimension , each embedding contains 768 numbers
#    Distance : Cosine => Metric used to measure similarity between vectors 
   
#    "Scan subdirectories" => The subdirectory logic is mainly used to automatically organize the documents into different source 
#    categories during ingestion
#    It helps the ingestion system : 
#    Scan folders automatically 
#    identify document categories/source types 
#    process grouped documents separately without manually specifying each category 
#    "true" => trusted/clean documents 
#    "noisy" => noisy/unverified documents 

# 5) process_directory : 
#    This function processes all files inside one directory/folder . 
#    It says "Go inside this folder,find all files and process them one by one"

#    This function scans a directory, filters only valid files,logs the file count and processes each file individually 
#    by calling the file level ingestion pipeline function responsible for parsing, chunking,embedding and indexing.

# 6) __name__ = "__main__"
#    This is the entry point of your ingestion pipeline 
#    When this file is run directly from terminal, start the ingestion pipeline 

#    This block acts as the command line entry point for the ingestion pipeline . It reads runtime arguments such as target directory, 
#    source type ,and wipe options , validates the directory and then triggers the universal ingestion pipeline that processes 
#    and indexes documents into Qdrant 

#    Command:
#     python -m app.ingestion.processor [directory_path] [source_type] [--wipe] => Run this Python module from terminal and optionally 
#     provide directory path, source type, and wipe option.
   

