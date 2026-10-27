FROM python:3.11-slim

WORKDIR /runner

# Minimal dependencies for code execution
RUN pip install --no-cache-dir pytest

# Create a non-root user for code execution
RUN useradd --create-home --no-log-init runner
USER runner

EXPOSE 8004

COPY services/code_runner.py .

CMD ["python", "code_runner.py"]
