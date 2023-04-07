FROM ghcr.io/clamsproject/clams-python:0.5.3

RUN pip3 install beautifulsoup4===4.9.3

WORKDIR ./app

COPY ./ ./

CMD ["python3", "app.py"]
