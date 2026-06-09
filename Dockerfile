# This dockerfile is used to create a docker image for your fastapi application

FROM python:3.11
# "Start with an image that already has python 3.11 installed"
# Empty machine + Python 3.11 = Base Docker Image"

WORKDIR /app 
# Creates ( if needed) and moves into the /app directory inside the container

COPY . . 
# COPY <source> <destination>
# ie Current Project Folder  ---> /app

RUN pip install -r requirements.txt  --no-cache-dir
# Runs during image build
# Docker installs the requirements
# --no-cache-dir => Package downloaded -> Package installed -> Cache deleted
# Without cache dir => Package downloaded -> Package installed -> Cache retained
#     This keeps the docker image smaller 

CMD ["uvicorn","app.main:app","--host","0.0.0.0","--port","8080"]
# Runs when the container starts
# uvicorn => ASGI server used to run the FASTAPI 
# 8080 is the port which our container will be running


# What happens when the Docker runs?
#   Container starts
#   Execute CMD
#   uvicorn app.main:app
#   FASTAPI starts
#   Listening on 0.0.0.0:8000

# In one sentence:
    # This dockerfile creates a python 3.11 container ,copies your fastapi project on it ,
    # install all dependencies from requirements.txt  and starts the fastapi application 
    # using uvicorn  on port 8080 