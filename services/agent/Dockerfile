FROM python:3.13-slim
WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
COPY services /app/services
COPY docs /app/docs
COPY prompts /app/prompts
RUN mkdir -p /app/data
EXPOSE 8002
CMD ["python", "-m", "services.agent.main"]
