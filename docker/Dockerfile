FROM python:3.12-slim

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Node.js (for pi-coding-agent)
RUN curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

# pi-coding-agent
RUN npm install -g @mariozechner/pi-coding-agent

# Data science libraries
RUN pip install --no-cache-dir \
    pandas \
    openpyxl \
    beautifulsoup4 \
    lxml \
    aiohttp \
    requests \
    pydantic \
    numpy

# Workspace directory
RUN mkdir /workspace
WORKDIR /workspace
