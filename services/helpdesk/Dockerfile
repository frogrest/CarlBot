FROM python:3.13-slim
WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
COPY services /app/services
COPY docs /app/docs
COPY prompts /app/prompts
RUN mkdir -p /app/data
EXPOSE 8000
CMD ["uvicorn", "services.helpdesk.app:app", "--host", "0.0.0.0", "--port", "8000"]
