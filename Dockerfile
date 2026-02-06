# Stage 1: Build the React frontend
FROM node:22-slim AS builder
WORKDIR /app/dashboard
COPY dashboard/package*.json ./
RUN npm install
COPY dashboard/ ./
RUN ls -la src/lib && npm run build

# Stage 2: Final image with Python and the built frontend
FROM python:3.11-slim
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Copy the built dashboard from the builder stage
COPY --from=builder /app/dashboard/dist ./dashboard/dist

# Ensure the server uses the PORT env var
EXPOSE 8080
CMD ["python3", "server.py"]
