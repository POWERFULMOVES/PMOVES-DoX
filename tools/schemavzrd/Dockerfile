FROM python:3.11-slim
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

EXPOSE 5174
ENV DB_URL="" OUTPUT_DIR="/app/out/schema"
CMD ["/usr/local/bin/entrypoint.sh"]
