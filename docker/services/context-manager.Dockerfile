FROM cahoots-base:latest

WORKDIR /app

CMD ["python", "-m", "services.context-manager.service"] 