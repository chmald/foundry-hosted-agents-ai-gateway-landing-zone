FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PORT=8080
WORKDIR /app
RUN groupadd --system app && useradd --system --gid app --home /app app
COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY . ./src/catalog-mcp
COPY profiles ./config/profiles
USER app
EXPOSE 8080
CMD ["python", "src/catalog-mcp/server.py"]
