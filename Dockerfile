FROM python:3.8-slim

WORKDIR /opt/app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Environment Variables

CMD [ "python", "./start.py"]
