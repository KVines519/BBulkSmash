# official Python base image with debian 12 bookworm
FROM python:3.13-slim-bookworm

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_HOME=/app \
    SIPP_VERSION=3.7.7 \
    SIPP_BIN_URL=https://github.com/SIPp/sipp/releases/download/v3.7.7/sipp

# Install system dependencies & clean-up (libcap2-bin for granting permissions using setcap)
RUN apt-get update && \
    apt-get install -y --no-install-recommends libcap2-bin nginx curl sngrep tcpdump && \
    rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR $APP_HOME

# Copy just requirements.txt first to leverage build cache
COPY requirements.txt .
RUN python -m pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
# Ensure you have a .dockerignore file to exclude unnecessary files!
COPY . .

# Download and install SIPp binary
RUN curl -L -o BBulkSmash/sipp ${SIPP_BIN_URL} && \
    chmod +x BBulkSmash/sipp

# Bundle xterm.js and addons as local static files (no CDN dependency at runtime)
RUN mkdir -p BBulkSmash/static/xterm && \
    curl -L -o BBulkSmash/static/xterm/xterm.min.css \
        https://cdn.jsdelivr.net/npm/@xterm/xterm@5.5.0/css/xterm.min.css && \
    curl -L -o BBulkSmash/static/xterm/xterm.min.js \
        https://cdn.jsdelivr.net/npm/@xterm/xterm@5.5.0/lib/xterm.min.js && \
    curl -L -o BBulkSmash/static/xterm/addon-fit.min.js \
        https://cdn.jsdelivr.net/npm/@xterm/addon-fit@0.10.0/lib/addon-fit.min.js && \
    curl -L -o BBulkSmash/static/xterm/addon-web-links.min.js \
        https://cdn.jsdelivr.net/npm/@xterm/addon-web-links@0.11.0/lib/addon-web-links.min.js

# Create /app/BBulkSmash/xml/tmp dir for tmp xml modification internally
RUN mkdir -p BBulkSmash/xml/tmp BBulkSmash/xml/backup logs db_data && \
    cp BBulkSmash/xml/*.xml BBulkSmash/xml/backup

# Collect static files (dummy key used only at build time for collectstatic)
RUN DJANGO_SECRET_KEY=build-time-placeholder python manage.py collectstatic --noinput

# Create non-root user
RUN addgroup --gid 1234 bbuser && \
    adduser --system --uid 5678 --gid 1234 --disabled-password --gecos "" bbuser

# Set ownership and permissions
RUN chown -R bbuser:bbuser $APP_HOME && \
    chown -R bbuser:bbuser /var/lib/nginx /var/log/nginx /run

# separate RUN for setcap as it sometimes did not work when combined with above RUN.    
RUN setcap cap_net_raw+eip $APP_HOME/BBulkSmash/sipp && \
    setcap cap_net_raw+eip /usr/bin/sngrep && \
    setcap cap_net_raw+eip /usr/bin/tcpdump

# Nginx configuration
COPY bbulksmash-nginx.conf /etc/nginx/sites-available/
RUN rm /etc/nginx/sites-enabled/default && \
    ln -s /etc/nginx/sites-available/bbulksmash-nginx.conf /etc/nginx/sites-enabled/

# Copy the entrypoint script
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Expose ports
EXPOSE 8080
EXPOSE 5060/udp 5060
EXPOSE 5061/udp 5061

# Switch to the non-root user before running the container
USER bbuser

# Set the entrypoint for the container
ENTRYPOINT ["/entrypoint.sh"]
