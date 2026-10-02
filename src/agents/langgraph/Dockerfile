FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PORT=8088
WORKDIR /app

RUN groupadd --system app && useradd --system --gid app --home /app app

COPY requirements.txt .
RUN python -m pip install --upgrade pip && python -m pip install --no-cache-dir -r requirements.txt --index-url https://pypi.org/simple

COPY *.py ./
COPY profiles ./config/profiles

USER app
EXPOSE 8088
CMD ["python", "main.py"]
