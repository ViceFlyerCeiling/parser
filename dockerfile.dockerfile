FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN playwright install chromium --with-deps
CMD ["python", "cli.py", "/config/config.yaml"]