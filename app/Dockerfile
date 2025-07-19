FROM python:3.11-slim
WORKDIR /workspace/app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
# Default command can be overridden by docker-compose
CMD ["python", "run.py"]