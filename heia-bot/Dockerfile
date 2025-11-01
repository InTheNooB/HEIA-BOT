FROM python:3.11.8-slim

# Timezone + dependencies
RUN apt-get update && apt-get install -y --no-install-recommends tzdata && rm -rf /var/lib/apt/lists/*
ENV TZ=Europe/Zurich
ENV PYTHONUNBUFFERED=1

# Working dir
WORKDIR /app

# Install deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy bot files
COPY . .


# Non-root user
RUN useradd -m appuser

# Make data writable by normal user
RUN mkdir -p /app/data && chown appuser:appuser /app/data

# Define what user to run as
USER appuser

CMD ["python", "bot.py"]
