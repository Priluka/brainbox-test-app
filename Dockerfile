FROM python:3.11-slim
RUN pip install requests
COPY main.py /app/main.py
WORKDIR /app
CMD ["python", "main.py"]
