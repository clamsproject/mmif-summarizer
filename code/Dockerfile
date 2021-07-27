FROM python:3.6-slim-buster

WORKDIR ./app

RUN pip3 install beautifulsoup4===4.9.3
RUN pip3 install lapps==0.0.2
RUN pip3 install clams-python==0.4.4

COPY ./ ./

CMD ["python3", "run.py"]
