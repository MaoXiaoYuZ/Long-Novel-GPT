FROM python:3.12-slim

WORKDIR /app

# Install nginx and iproute2
RUN apt-get update && apt-get install -y nginx iproute2 && rm -rf /var/lib/apt/lists/* \
    && rm -f /etc/nginx/sites-enabled/default \
    && rm -f /etc/nginx/sites-available/default

# Copy requirements first for better caching
COPY backend/requirements.txt .
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple
RUN pip install -r requirements.txt

# Copy backend files
COPY config.py .
COPY backend/app.py .
COPY backend/healthcheck.py .
COPY core/ ./core/
COPY llm_api/ ./llm_api/
COPY prompts/ ./prompts/
COPY custom/ ./custom/

# Copy frontend files
COPY frontend/index.html /usr/share/nginx/html/
COPY frontend/js/ /usr/share/nginx/html/js/
COPY frontend/styles/ /usr/share/nginx/html/styles/
COPY frontend/data/ /usr/share/nginx/html/data/

# Copy nginx configuration
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf

# Copy start script
COPY start.sh .
RUN chmod +x start.sh

# EXPOSE $FRONTEND_PORT

CMD ["./start.sh"] 