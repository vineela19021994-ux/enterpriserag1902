from email import contentmanager
from time import thread_time_ns
from contextlib import _T_fd_or_any_path
import io
# pyrefly: ignore [missing-import]
import logfire 
# pyrefly: ignore [missing-import]
from pypdf import PdfReader,PdfWriter
# pyrefly: ignore [missing-import]
from google.cloud import documentai
from app.config import Settings

client = documentai.DocumentProcessorServiceClient()
MAX_PAGES_PER_REQUEST = 15

def parse_pdf(file_path : str):
    """
    Parse the pdf using Google cloud document ai
    Automatically splits large pdfs into 15-page chunks to bypass synchronous API limits
    """

    with logfire.span("📄 Document AI Parsing", filename=file_path):
        try:
            reader = PdfReader(file_path)
            total_pages = len(reader.pages)
            logfire.info(f"Total pages : {total_pages}")

            name = client.processor_path(
                Settings.PROJECT_ID,
                Settings.GCP_DOC_AI_LOCATION,
                Settings.GCP_DOC_AI_PROCESSOR_ID
            )

            full_text = ""

            # If small enough , process entirely
            if total_pages<=MAX_PAGES_PER_REQUEST:
                with open(file_path,"rb") as f:
                    image_content = f.read()
                full_text = process_document_chunk(image_content,name)
            else :
                # Split into chunks of max pages per request
                logfire.info(f"PDF exceeds {MAX_PAGES_PER_REQUEST} pages. Splitting into chunks...")

                for i in range(0,total_pages,MAX_PAGES_PER_REQUEST):
                    writer = PdfWriter()
                    chunk_end = min(i+MAX_PAGES_PER_REQUEST,total_pages)

                    for page_num in range(i,chunk_end):
                        writer.add_page(reader.pages[page_num])

                    # Writer chunk to bytes
                    with io.BytesIO() as bytes_stream:
                        writer.write(bytes_stream)
                        chunk_bytes = bytes_stream.getvalue()

                    with logfire.span(f"Processing pages {i+1} to {chunk_end}"):
                        chunk_text = process_document_chunk(chunk_bytes, name)
                        full_text += chunk_text + "\n"
                
            if not full_text.strip():
                logfire.warning(f"⚠️ Document AI returned empty text for {file_path}")
            else :
                logfire.info(f"✅ Document AI successfully parsed {len(full_text)} characters")

            return full_text
        
        except Exception as e:
            logfire.error(f"❌ Document AI Parse Failed: {e}")
            logfire.info("💡 Ensure the Processor ID is correct and the API is enabled.")
            raise e

def process_document_chunk(image_content : bytes, name : str) -> str:
    """
    Helper function to send a specific byte chunk to Document AI
    """
    raw_document = documentai.RawDocument(
        content = image_content,
        mime_type = "application/pdf"
    )

    request = documentai.ProcessRequest(
        name = name,
        raw_document = raw_document
    )

    result = client.process_document(request = request)
    return result.document.text
            
    
# 1) IO -> for input and output operations
# 2) Here we used Pyfreader and pdfwriter because we want to read and write pdfs
# 3) document ai => to process the Pdf
# 4) From configuration ie config file import settings
# 5) Document ai is the google cloud service which we are using to parse the pdfs
#    Document ai only process 15 pages of the Pdf, if it is larger it will not take the pdf 
#    as the input because document ai is designed such a way that it can perform the best on top 
#    15 pages only 
#    Our pdf which we are using here have 190-300 pages 
#    That is the reason we have used pdfwriter 
#    So this 190-300 pages we are going to divide into 15 pages each so that we can properly feed this 
#    into document ai 
# 6) In parse_pdf :
#    Read the pdf file and check the length
#    Then import the document ai details from config file 
#    It checks for total pages and if it is less than 15 pages , then open the pages and process the document.
#    To process the document chunk we have "process document chunk", it will take the image content
#    and name of the file and return a str and process the document.

# 7) If the pages are greater than 15 
# then it is going to split the pdf into chunks
# and then process each document chunk using "process document chunk"



