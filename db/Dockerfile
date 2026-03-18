FROM python:3.12-slim

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        curl \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

COPY pyproject.toml uv.lock ./
COPY db/pyproject.toml ./db/
COPY api/pyproject.toml ./api/
COPY scraper/pyproject.toml ./scraper/
COPY nlp/pyproject.toml ./nlp/
COPY dags/pyproject.toml ./dags/

RUN uv venv /opt/venv \
    && . /opt/venv/bin/activate \
    && uv sync \
        --frozen \
        --no-dev \
        --package jmie-db \
        --active

ENV PATH="/opt/venv/bin:$PATH"

COPY db/ ./db/

RUN chmod +x db/scripts/init.sh

RUN groupadd -r dbuser && useradd -r -g dbuser dbuser
RUN chown -R dbuser:dbuser /app /opt/venv
USER dbuser

CMD ["bash", "db/scripts/init.sh"]