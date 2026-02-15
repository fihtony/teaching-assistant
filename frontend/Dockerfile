# Frontend Dockerfile for Teaching Assistant Grading System

# Build stage
FROM node:22-alpine as builder

WORKDIR /app

# Copy package files
COPY package.json package-lock.json ./

# Install dependencies
RUN npm ci

# Copy source code
COPY . .

# Build application
RUN npm run build

# Runtime stage
FROM node:22-alpine

WORKDIR /app

# Create non-root user (check if exists first to avoid conflicts)
RUN addgroup -g 2000 appuser 2>/dev/null || true && \
    adduser -D -u 2000 -G appuser appuser

# Install serve to serve static files (lightweight alternative to running dev server)
RUN npm install -g serve

# Copy built application from builder
COPY --from=builder --chown=appuser:appuser /app/dist ./dist

# Switch to non-root user
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://localhost:3090/ || exit 1

# Expose port
EXPOSE 3090

# Run application
CMD ["serve", "-s", "dist", "-l", "3090"]
