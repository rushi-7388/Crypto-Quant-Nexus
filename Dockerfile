# Streamlit hub + all analytics apps (port 8501). API uses Dockerfile.api.
FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
COPY quant_core/ ./quant_core/
COPY nexus-hub/ ./nexus-hub/
COPY mm-engine/ ./mm-engine/
COPY funding-radar/ ./funding-radar/
COPY flow-alpha/ ./flow-alpha/
COPY vol-surface/ ./vol-surface/
COPY regime-nexus/ ./regime-nexus/
COPY alpha-terminal/ ./alpha-terminal/
COPY ops-dashboard/ ./ops-dashboard/
COPY .streamlit/ ./.streamlit/

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8501
ENV STREAMLIT_SERVER_PORT=8501
CMD ["streamlit", "run", "nexus-hub/app.py", "--server.address=0.0.0.0"]
