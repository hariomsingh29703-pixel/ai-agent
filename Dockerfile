# ── Stage 1: Base image with Python 3.11 ──────────────────────────────────
FROM python:3.11-slim

# Install system dependencies required by Playwright + Chromium
RUN apt-get update && apt-get install -y \
    wget curl gnupg ca-certificates \
    libnss3 libatk1.0-0 libatk-bridge2.0-0 \
    libcups2 libdrm2 libxkbcommon0 libxcomposite1 \
    libxdamage1 libxrandr2 libgbm1 libasound2 \
    libpango-1.0-0 libcairo2 libx11-xcb1 \
    fonts-liberation libappindicator3-1 xdg-utils \
    --no-install-recommends && rm -rf /var/lib/apt/lists/*

# ── Stage 2: Set working directory ─────────────────────────────────────────
WORKDIR /app

# ── Stage 3: Install Python dependencies ───────────────────────────────────
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Stage 4: Install Playwright Chromium browser ───────────────────────────
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
RUN playwright install chromium

# ── Stage 5: Copy application source code ──────────────────────────────────
COPY . .

# ── Stage 6: Create writable data and workspace directories ────────────────
RUN mkdir -p data workspace

# ── Stage 7: Expose port and start FastAPI with uvicorn ────────────────────
ENV PORT=8080
ENV PLAYWRIGHT_HEADLESS=true
EXPOSE 8080

CMD ["python", "app.py"]
