FROM python:3.12-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 \
PYTHONUNBUFFERED=1
WORKDIR /opt/cf-ip-optimizer
CMD ["python", "--version"]
