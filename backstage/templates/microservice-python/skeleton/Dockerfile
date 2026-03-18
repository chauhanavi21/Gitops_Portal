FROM python:${{ values.pythonVersion }}-slim AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --target=/app/deps -r requirements.txt

FROM python:${{ values.pythonVersion }}-slim
RUN groupadd -r appgroup && useradd -r -g appgroup appuser
WORKDIR /app
COPY --from=builder /app/deps /usr/local/lib/python${{ values.pythonVersion }}/site-packages
COPY . .
USER appuser
EXPOSE ${{ values.port }}
HEALTHCHECK --interval=10s --timeout=3s CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:${{ values.port }}/healthz')" || exit 1
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "${{ values.port }}"]
