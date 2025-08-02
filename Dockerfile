# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies including FFmpeg
RUN apt-get update && apt-get install -y \
    ffmpeg \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better Docker layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the bot code and all modules
COPY bot.py .
COPY config/ ./config/
COPY utils/ ./utils/
COPY cogs/ ./cogs/

# Create non-root user for security
RUN useradd -m -u 1000 botuser && chown -R botuser:botuser /app
USER botuser

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Health check to ensure bot is running
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
  CMD python -c "import psutil, os; p = psutil.Process(os.getpid()); print('Bot is running, Memory:', p.memory_info().rss // 1024 // 1024, 'MB')" || exit 1

# Run the bot
CMD ["python", "bot.py"]