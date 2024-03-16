FROM python:3.10-slim

RUN mkdir /app
WORKDIR /app

COPY requirements.txt /app
RUN pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

COPY memos.py /app
COPY config_demo.ini /app/config.ini

CMD ["python3","/app/memos.py"]