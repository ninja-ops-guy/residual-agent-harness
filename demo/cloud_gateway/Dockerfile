FROM python:3.12-slim
WORKDIR /app
COPY demo/cloud_gateway/server.py /app/server.py
ENV PYTHONUNBUFFERED=1 PORT=8080
EXPOSE 8080
CMD ["python3", "/app/server.py"]
