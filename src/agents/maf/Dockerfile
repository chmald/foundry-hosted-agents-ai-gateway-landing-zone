FROM python:3.12-slim

# Packages come from PyPI. Override for a slow or blocked network, for example:
#   docker build --build-arg PIP_INDEX_URL=https://<mirror>/simple/ .
ARG PIP_INDEX_URL=https://pypi.org/simple
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PORT=8088
WORKDIR /app

RUN groupadd --system app && useradd --system --gid app --home /app app

COPY requirements.txt .
RUN python -m pip install --upgrade pip --index-url ${PIP_INDEX_URL} && python -m pip install --no-cache-dir --pre -r requirements.txt --index-url ${PIP_INDEX_URL}

# The official host keeps response state under ~/.agentserver (HOME=/app), so the non-root user must own /app.
RUN chown app:app /app
COPY *.py ./
COPY profiles ./config/profiles

USER app
EXPOSE 8088
CMD ["python", "main.py"]
