FROM python:3.12-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgl1 \
    libglib2.0-0 \
    tesseract-ocr \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.12-slim AS libredwg

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    autoconf \
    libtool \
    pkg-config \
    texinfo \
    wget \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && wget -qO /tmp/libredwg.tar.gz \
       https://ftp.gnu.org/gnu/libredwg/libredwg-0.13.tar.gz \
    && tar xzf /tmp/libredwg.tar.gz -C /tmp \
    && cd /tmp/libredwg-0.13 \
    && ./configure --prefix=/usr --disable-static --disable-rust \
    && make -j$(nproc) \
    && make install \
    && rm -rf /tmp/libredwg*

FROM python:3.12-slim AS runner

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    tesseract-ocr \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=libredwg /usr/bin/dxf2dwg /usr/bin/dxf2dwg
COPY --from=libredwg /usr/lib/libredwg.so* /usr/lib/

RUN groupadd -r cadora && useradd -r -g cadora -d /app cadora

COPY --chown=cadora:cadora . .

RUN mkdir -p /app/logs /app/uploads \
    && chown -R cadora:cadora /app/logs /app/uploads /app/alembic

USER cadora

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v1/health')"

ENTRYPOINT ["/app/entrypoint.sh"]
