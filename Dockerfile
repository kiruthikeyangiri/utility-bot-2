# Stage 1: Build the React Client
FROM node:20-alpine AS frontend-builder
WORKDIR /app/client
COPY client/package*.json ./
RUN npm ci
COPY client/ ./
RUN npm run build

# Stage 2: Python FastAPI Backend + OCR Runtime
FROM python:3.11-slim
WORKDIR /app

# Install system dependencies for OpenCV and image operations
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Install Python requirements
COPY python_service/requirements.txt ./python_service/
RUN pip install --no-cache-dir -r python_service/requirements.txt

# Copy Python backend code
COPY python_service/ ./python_service/

# Copy built React frontend into client/dist
COPY --from=frontend-builder /app/client/dist ./client/dist

WORKDIR /app/python_service

ENV PORT=8000
EXPOSE 8000

CMD ["python", "main.py"]
