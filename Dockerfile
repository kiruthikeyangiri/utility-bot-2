# Stage 1: Build the React Client
FROM node:20-alpine AS frontend-builder
WORKDIR /app/client
COPY client/package*.json ./
RUN npm install
COPY client/ ./
RUN npm run build

# Stage 2: Python FastAPI Backend + OCR & Vision AI Runtime
FROM python:3.11-slim
WORKDIR /app

# Install system dependencies for OpenCV, PyTorch, ONNX Runtime, and ZXing
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    libsm6 \
    libxrender1 \
    libxext6 \
    && rm -rf /var/lib/apt/lists/*

# Install Python requirements
COPY python_service/requirements.txt ./python_service/
RUN pip install --no-cache-dir -r python_service/requirements.txt

# Copy Python backend code
COPY python_service/ ./python_service/

# Copy built React frontend into client/dist and python_service/dist
COPY --from=frontend-builder /app/client/dist ./client/dist
COPY --from=frontend-builder /app/client/dist ./python_service/dist

WORKDIR /app/python_service

ENV PORT=8000
EXPOSE 8000

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
