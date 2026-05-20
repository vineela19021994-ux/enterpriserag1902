# pyrefly: ignore [missing-import]
from bs4 import BeautifulSoup
# pyrefly: ignore [missing-import]
import logfire

# pyrefly: ignore [parse-error]
def parse_html(file_path : str):
    """
    Parses HTML content using BeautifulSoup.
    Cleans scripts , styles , and extracts readable text for RAG
    """
    with logfire.span("📄 HTML Parsing", filename=file_path):
        try:
            with open(file_path,'r',encoding = 'utf-8',errors='ignore') as f :
                content = f.read()
            soup = BeautifulSoup(content,"html.parser")

            # Remove junk (scripts, styles, metadata)

            for script in soup(["script","style","meta","noscript"]):
                script.decompose()
            
            # Extract text 
            text = soup.get_text(separator = "\n")

            # Clean  Whitespace (Collapse multiple new lines)
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text_clean = '\n'.join(chunk for chunk in chunks if chunk)

            return text_clean
        
        except Exception as e :
            logfire.error(f"❌ HTML Parse Failed: {e}")
            raise e
    

# 1) Beautiful Soup is used for web scraping and also used to parse HTML documents
# 2) Here we are using logfire to log each and every part
# 3) Here it is going to pay attention only to the text , ignore colour style and all
# 4) Initializing beautiful soup class and passing the content
# 5) Content is nothing but which we have received from html file and using html.parser here
# 6) And we are iterating on the content and, we are going to extract the script,style, meta,
#    noscript and we will decompose ie remove them
# 7) Using get_text function we will extract all the text and going to separate every where,
#    where there is a new line
# 8) For each line we will strip the line using splitlines
# 9) We will chunk them and join all the clean chunks from the html file  
 
