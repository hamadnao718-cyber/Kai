# OpenManus MCP Server — Dockerfile
#
# Builds the openmanus/ MCP server image for use with docker-compose.yml.
# Expects OpenManus source code to be cloned in openmanus/src:
#   git clone https://github.com/hamadnao718-cyber/OpenManus openmanus/src

FROM python:3.12-slim

# System dependencies required by Playwright / Chromium
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    gnupg \
    ca-certificates \
    libglib2.0-0 \
    libnss3 \
    libnspr4 \
    libdbus-1-3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxcb1 \
    libxkbcommon0 \
    libx11-6 \
    libxcomposite1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /openmanus

# Install Python dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers
RUN playwright install chromium --with-deps

# Copy the MCP server entrypoint and configuration template
COPY mcp_server.py ./
COPY config/config.example.toml ./config/config.example.toml

# Mount OpenManus source (cloned externally) at /openmanus/src
# so the app.* imports resolve correctly.
COPY src/ ./src/

ENV PYTHONPATH=/openmanus/src

EXPOSE 8765

CMD ["python", "mcp_server.py"]
