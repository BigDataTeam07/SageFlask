FROM python:3.7-slim

# install build-essential for compiling
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
 && rm -rf /var/lib/apt/lists/*

# copy the current directory contents into the container at /app
WORKDIR /app
COPY . /app

# install pip requirements
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

EXPOSE 8080

# set environment variables
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:8080"]
