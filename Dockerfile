# If deploying on Railway, environment variables are set from the secrets UI
# and are injected in during build.
# ARG DISCORD_BOT_TOKEN

FROM python:3.8-slim

ARG COMMIT_HASH

WORKDIR /opt/app

# Install git for discord.py installation from GitHub
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Expose port for Flask service
EXPOSE 5000

# Use a startup script to run both services
CMD [ "python", "./start.py"]