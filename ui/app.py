import os # to interact with the libraries
import streamlit as st
import requests
import time
import uuid # to initialize a new thread always 
import logfire # for maintaining logs
from dotenv import load_dotenv # for loading the environment variables 


# Load environment variables explicitly from the root directory

# Here we are setting the absolute path and load the .env variables
env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".env"))
load_dotenv(dotenv_path=env_path)


# Initialize Logfire
# We have to get the logfire token 
try:
    token = os.getenv("LOGFIRE_TOKEN")
    if not token:
        print("ERROR: LOGFIRE_TOKEN is empty or None!")
    logfire.configure(token=token)
    # If the logfire token is detected we will display message " Connected and Tracing"
    # logfire.instrument_requests() # Disabled due to OpenTelemetry bug on Windows: MeterProvider.get_meter() got multiple values for argument 'version'
    LOGFIRE_STATUS = "Connected & Tracing"
except Exception as e:
    print(f"Logfire Init Error in UI: {e}")
    LOGFIRE_STATUS = f"Standby (Error: {e})"
    


# --- PAGE CONFIG ---
st.set_page_config(
    page_title="Enterprise Agentic RAG",
    page_icon="🤖",
    layout="wide",
)

# --- AVATARS ---
AI_AVATAR = "🤖"
USER_AVATAR = "👤"


# --- SESSION MANAGEMENT ---
# Here we are initializing a session
# We are initializing a new session with a new thread id to maintain a user history and 
#    we will log that new user session has been created
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
    logfire.info(f"✨ New User Session Created: {st.session_state.session_id}")

# If messages are not in session state we will initialize a new session state messages
if "messages" not in st.session_state:
    st.session_state.messages = []


# --- SIDEBAR ---
# In the side bar it is going to display the logfire status and memory id 
with st.sidebar:
    st.title("🧠 Agent OS")
    st.markdown("---")
    st.success(f"Logfire: {LOGFIRE_STATUS}")
    st.info(f"Memory ID: {st.session_state.session_id[:8]}")
    
    # We have a button for clearing the history and memory , it is going to erase all the memory
    # clear chat messages
    # Generate a new session id 
    # Immediately re-runs the streamlit application from the top so UI updates and shows the  cleared state
    if st.button("🗑️ Clear History & Memory", width="stretch", type="primary"):
        logfire.warn(f"🗑️ Memory Wipe Triggered for session: {st.session_state.session_id}")
        st.session_state.messages = []
        st.session_state.session_id = str(uuid.uuid4())
        st.rerun()

# --- MAIN CHAT ---
st.title("🤖 Enterprise Agentic Assistant")


# Display history
# The messages that are coming in the session_messages, we are going to display all of that 
# If the message is from AI , it is going to say AI 
#    IF user , it is going to say user 
for message in st.session_state.messages:
    avatar = AI_AVATAR if message["role"] == "assistant" else USER_AVATAR
    with st.chat_message(message["role"], avatar=avatar):
        st.markdown(message["content"])

# Chat Input
if prompt := st.chat_input("Ask about your documentation..."):
    # START TRACE: User Interaction
    # User interaction started here 
    with logfire.span("💬 User Chat Interaction", user_query=prompt, session_id=st.session_state.session_id):
        
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user", avatar=USER_AVATAR):
            st.markdown(prompt)

        # Assistant Response
        # The moment chat message is received , we will say the agent is thinking
        with st.chat_message("assistant", avatar=AI_AVATAR):
            with st.status("🔍 Agent is thinking...", expanded=True) as status:
                try:
                    # DISTRIBUTED TRACE: Calling Backend
                    with logfire.span("📡 Calling RAG Backend"):
                        # Get backend URL from env, or default to local if not set
                        base_url = os.getenv("BACKEND_URL", "http://localhost:8000")
                        url = f"{base_url}/query"
                        # For the prompt and the thread id we will send a post request and we will 
                        #     trigger a response
                        payload = {"q": prompt, "thread_id": st.session_state.session_id}
                        response = requests.post(url, json=payload, timeout=60)
                        data = response.json()
                    
                    # Show Reasoning Steps from Backend
                    steps = data.get("thought_process", [])
                    for step in steps:
                        st.write(f"⚙️ {step}")
                    
                    status.update(label="✅ Answer Synthesized", state="complete", expanded=False)
                    
                    # --- SHOW SOURCES (NESTED EXPANDABLES) ---
                    # All the docs it has retrieved it will give the information 
                    sources = data.get("sources", [])
                    if sources:
                        with st.expander("📄 View Retrieved Context (Sources)"):
                            for i, source in enumerate(sources):
                                # Create a preview title for each chunk where it shows only the first 100 characters 
                                preview = source[:100].replace("\n", " ") + "..."
                                # and here an expander is created so that we dnt have to see the whole docs always
                                with st.expander(f"Chunk {i+1}: {preview}"):
                                    st.info(source)
                except Exception as e:
                    logfire.error(f"❌ UI-Backend Connection Failed: {e}")
                    status.update(label="❌ Connection Failed", state="error")
                    st.error("Backend Offline.")
                    st.stop()

            # Final Answer Streaming
            answer_placeholder = st.empty()
            full_answer = data.get("answer", "No response.")
            
            curr_text = ""
            for char in full_answer:
                curr_text += char
                answer_placeholder.markdown(curr_text + "▌")
                time.sleep(0.005)
            
            answer_placeholder.markdown(full_answer)
            st.session_state.messages.append({"role": "assistant", "content": full_answer})
            logfire.info("✅ Chat cycle completed successfully.")



# Q) What is setting the absolute path when loading the .env file ?
   
#    os.path.abspath() converts the relative path into a full absolute path from the root 
#    of your file system.
#    Suppose your file is located at:   C:\Projects\MyApp\app\main.py
#    Then:   os.path.dirname(__file__)
#    returns:  C:\Projects\MyApp\app
#    Adding ".." moves one folder up:  C:\Projects\MyApp
#    Adding ".env" gives: C:\Projects\MyApp\.env
#    Finally: 
#    os.path.abspath(...) returns the full absolute path: C:\Projects\MyApp\.env
#    Why use absolute path ? It makes your code independent of the execution location


# Assistant Response
# Either we can have a "backend url" or it will run on localhost 
# Once we make the app , we can run locally or we can also run in on a docker container 
# When we run locally it will run on 8000 port(fastapi)
# But when we run it on docker container , it will run on "cloudrun" and this cloud run will
#    be giving a url ie the "backend url"



