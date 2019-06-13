FROM python:3.6-stretch

RUN mkdir -p /app
WORKDIR /app

ADD requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN python -m spacy download en_core_web_sm
RUN python -m spacy download en_core_web_md
RUN python -m spacy link en_core_web_md en
ADD entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh; \
    chmod +x ./interact.sh

ADD . .


ENTRYPOINT ["/entrypoint.sh"]