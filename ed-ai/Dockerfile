FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml .
RUN pip install --no-cache-dir .

COPY ed_ai/ ed_ai/

EXPOSE 4243

CMD ["uvicorn", "ed_ai.app:app", "--host", "0.0.0.0", "--port", "4243"]
