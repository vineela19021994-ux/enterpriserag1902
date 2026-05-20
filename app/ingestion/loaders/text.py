# pyrefly: ignore [missing-import]
import logfire

def parse_text(file_path : str):
    """
    Parses plain text files.
    """
    with logfire.span("📄 Text Parsing", filename = file_path):
        try:
            with open(file_path,'r',encoding='utf-8',errors='ignore') as f:
                return f.read()
        except Exception as e :
            logfire.error(f"❌ Text Parse Failed : {e}")
            raise e

# Here we are writing a func to parse text
# It takes text file as an input
# It something goes wrong raise and exception on logfire it self , dnt print in the terminal
# If successful , logfire displays "Text parsing"
# It will open and read the file 