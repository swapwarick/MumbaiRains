# --- Stage 1: Build the React Frontend ---
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# --- Stage 2: Serve API and Frontend from Python FastAPI ---
FROM python:3.12-slim
WORKDIR /app

# Install system dependencies needed for spatial libraries if needed
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgdal-dev \
    && rm -rf /var/lib/apt/lists/*

# Set GDAL env variables
ENV GDAL_VERSION=3.8.4

# Install python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend and simulation source
COPY backend/ ./backend
COPY simulation/ ./simulation
COPY data/ ./data
COPY scripts/ ./scripts

# Copy frontend static distribution from builder stage
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# Generate initial mock GIS datasets if they don't exist
RUN python scripts/generate_mock_gis_data.py

EXPOSE 8000
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
