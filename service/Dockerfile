FROM python:3.10-alpine

COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt

COPY ./app ./app

EXPOSE 80

ENTRYPOINT ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "80"]