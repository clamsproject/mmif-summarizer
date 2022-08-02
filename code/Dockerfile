FROM python:3.8-slim-buster

RUN pip3 install clams-python==0.5.1
RUN pip3 install beautifulsoup4===4.9.3

WORKDIR ./app

COPY ./ ./

CMD ["python3", "run.py"]
