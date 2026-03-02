# Multi-stage Dockerfile for JMIE React Frontend
# Supports multi-platform builds: linux/amd64, linux/arm64
# Production-optimized with minimal image size and security best-practices

# ===== Stage 1: Build React App =====
FROM node:18-alpine as builder

# Set working directory
WORKDIR /build

# Install build dependencies
RUN apk add --no-cache \
    python3 \
    make \
    g++

# Copy package files
COPY package.json package-lock.json ./

# Install dependencies with npm ci (clean install for reproducible builds)
RUN npm ci

# Copy source code
COPY . .

# Build the React application
# NODE_ENV=production enables optimizations like minification
RUN NODE_ENV=production npm run build

# ===== Stage 2: Serve with Nginx =====
FROM nginx:alpine

# Set environment variables
ENV NODE_ENV=production
ENV TZ=UTC

# Set working directory
WORKDIR /usr/share/nginx/html

# Install runtime dependencies only
RUN apk add --no-cache \
    curl \
    tini

# Create non-root user for security
RUN addgroup -g 101 -S nginx-app && \
    adduser -S -D -H -u 101 -h /var/cache/nginx -s /sbin/nologin -G nginx-app -g "nginx app" _nginx-app

# Copy Nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy built application from builder stage
COPY --from=builder --chown=_nginx-app:nginx-app /build/dist /usr/share/nginx/html

# Copy any static assets (if they exist)
RUN if [ -d public ]; then cp -r public/. /usr/share/nginx/html/; fi && \
    chown -R _nginx-app:nginx-app /usr/share/nginx/html

# Change ownership of nginx cache and pid directories
RUN chown -R _nginx-app:nginx-app /var/cache/nginx /run /var/log/nginx

# Create nginx worker directory
RUN mkdir -p /var/run/nginx && chown -R _nginx-app:nginx-app /var/run/nginx

# Expose port
EXPOSE 3000

# Health check - verify Nginx is responsive
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:3000/ || exit 1

# Use tini to handle signals properly
ENTRYPOINT ["/sbin/tini", "--"]

# Start Nginx in foreground
CMD ["nginx", "-g", "daemon off;"]
