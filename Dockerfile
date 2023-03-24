# If deploying on Railway, environment variables are set from the secrets UI
# and are injected in during build.
# ARG DISCORD_BOT_TOKEN

FROM python:3.8-slim

WORKDIR /opt/app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD [ "python", "./start.py"]