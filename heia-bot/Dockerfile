# ---- base image ----
  FROM python:3.11-slim

  # ---- working directory ----
  WORKDIR /app
  
  # ---- copy project files ----
  COPY requirements.txt .
  RUN pip install --no-cache-dir -r requirements.txt
  
  COPY . .
  
  # ---- environment variables ----
  # These can be overridden by Docker secrets or your host
  ENV PYTHONUNBUFFERED=1
  
  # ---- run the bot ----
  CMD ["python", "bot.py"]
  