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

CMD ["python", "bot.py"]
