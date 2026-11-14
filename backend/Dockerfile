FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    DATA_DIR=/data \
    HOME=/home/app

RUN useradd --create-home --uid 1000 app && mkdir /data && chown app /data
WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app ./app
USER app

# Pre-fetch the ChromaDB embedding model so first use needs no network.
RUN python -c "from chromadb.utils.embedding_functions import DefaultEmbeddingFunction as F; F()(['warmup'])"

VOLUME /data
EXPOSE 8000
CMD ["uvicorn", "app.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
