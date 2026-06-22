ARG BUILD_FROM
FROM $BUILD_FROM

ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apk add --no-cache \
    python3 \
    py3-pip

COPY requirements.txt .
RUN pip3 install --no-cache-dir --break-system-packages -r requirements.txt

COPY alpaca_bridge ./alpaca_bridge

COPY run.sh /
RUN chmod a+x /run.sh

CMD [ "/run.sh" ]
