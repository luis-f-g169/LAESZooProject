FROM python:3.11-slim

WORKDIR /app
COPY . .

RUN pip install fastapi uvicorn

EXPOSE 8443

CMD ["uvicorn", "main.websiteLAES:app", "--host", "0.0.0.0", "--port", "8443", "--ssl-certfile", "localhost+2.pem", "--ssl-keyfile", "localhost+2-key.pem"]
