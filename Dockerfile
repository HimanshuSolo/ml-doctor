# MLDoctor — one-process dashboard (prebuilt Next.js frontend in static_next).
# Build:  docker build -t mldoctor .
# Run:    docker run --rm -p 8765:8765 mldoctor
# Open:   the http://127.0.0.1:8765/?token=... URL printed in `docker logs`.
FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 MLDOCTOR_ALLOW_NONLOCAL=1
WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
COPY fixtures ./fixtures
RUN pip install --index-url https://download.pytorch.org/whl/cpu torch && pip install ".[fixtures]" && mkdir -p uploads
EXPOSE 8765
HEALTHCHECK --interval=15s --timeout=3s --start-period=20s \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8765/', timeout=2)"
CMD ["mldoctor", "serve", "--host", "0.0.0.0", "--port", "8765"]
