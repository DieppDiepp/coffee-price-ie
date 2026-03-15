FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV DEBIAN_FRONTEND=noninteractive

# Set the working directory
WORKDIR /app

# Install system dependencies (build tools, libpq, etc. if needed)
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies first to cache them
COPY requirements.txt /app/
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Install ML dependencies from Kaggle notebook
RUN pip install trafilatura bs4 underthesea huggingface_hub
RUN pip install transformers accelerate bitsandbytes torch

# Copy the rest of the application code
COPY . /app/

# The runner.py script creates required data directories
# The default command runs the newly created runner.py
CMD ["python", "runner.py", "--model", "qwen"]