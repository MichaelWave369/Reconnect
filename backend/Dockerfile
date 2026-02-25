FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
COPY main.py ./main.py
ENV RECONNECT_DB=/app/data/reconnect.db
ENV RECONNECT_UPLOAD_DIR=/app/data/uploads
EXPOSE 8000
CMD ["python", "main.py"]
