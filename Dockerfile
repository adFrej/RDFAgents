FROM python:3.9-alpine

EXPOSE 10000

COPY . /app
WORKDIR /app

RUN pip install --no-cache -r requirements.txt

CMD ["python", "main.py"]
