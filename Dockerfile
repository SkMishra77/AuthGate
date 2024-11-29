# Use a lightweight Python image
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies for Python
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (cache dependencies)
COPY requirements.txt .

# Create a virtual environment
RUN python -m venv /venv

# Activate virtual environment and install dependencies
RUN /venv/bin/pip install --upgrade pip && \
    /venv/bin/pip install -r requirements.txt

# Copy the application files
COPY . .

# Set the virtual environment path
ENV PATH="/venv/bin:$PATH"

# Expose the port for FastAPI
EXPOSE 8000

# Command to run FastAPI
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
