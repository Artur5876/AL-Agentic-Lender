FROM python:3.12-slim
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/app ./app
COPY ai/calc ./ai/calc
COPY ai/common ./ai/common
COPY ai/valuation ./ai/valuation
ENV PYTHONPATH=/app/ai
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
