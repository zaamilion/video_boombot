FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV APP_HOME /app

WORKDIR $APP_HOME

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Create media directories
RUN mkdir -p \
    $APP_HOME/assets \
    $APP_HOME/myinstants_sounds \
    $APP_HOME/videos \
    $APP_HOME/results

# Create non-root user and switch
RUN groupadd -r appuser && useradd -r -g appuser appuser \
    && chown -R appuser:appuser $APP_HOME
USER appuser

CMD ["python", "bot.py"]