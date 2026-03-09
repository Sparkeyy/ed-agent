FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml .
RUN pip install --no-cache-dir .

COPY ed_engine/ ed_engine/

EXPOSE 4242

CMD ["uvicorn", "ed_engine.app:app", "--host", "0.0.0.0", "--port", "4242"]
