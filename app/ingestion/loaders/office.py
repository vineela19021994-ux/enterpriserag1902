# pyrefly: ignore [missing-import]
import logfire
# pyrefly: ignore [missing-import]
from unstructured.partition.auto import partition

def parse_office(file_path : str):
    """
    Parses office documents (.docx,.pptx) using the unstructured library.
    Unlike pdfs , these formats are structured and light weight, so they are processed locally
    """
    with logfire.span("📄 Office Document Parsing", filename=file_path):
        try :
            # Unstructured automatically detects if its a docx or pptx
            elements = partition(filename = file_path)
            full_text = "\n".join([str(el) for el in elements])

            if not full_text.strip():
                logfire.warning(f"⚠️ Unstructured returned empty text for {file_path}")
            else:
                logfire.info(f"✅ Successfully parsed {len(full_text)} characters")

            return full_text
        except Exception as e :
            logfire.error(f"❌ Office Parse Failed: {e}")
            raise e


# 1) Here we are using unstructured library and partition method 
#    document ai will be processed on cloud 
#    and this will be processed locally 
# 2) partition reads the documents and breaks it into structured elements
#    then convert all elements into one text
#    and removes white spaces or new lines using strip()
# 3) Then checks if the parsing returned empty  text ie document extraction failed
#    else document extraction is successful.



