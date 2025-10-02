FROM rust:1-bookworm AS build
RUN apt-get update && apt-get install -y --no-install-recommends pkg-config libssl-dev ca-certificates && rm -rf /var/lib/apt/lists/*
RUN cargo install schemavzrd --locked || cargo install schemavzrd

FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates python3 && rm -rf /var/lib/apt/lists/*
COPY --from=build /usr/local/cargo/bin/schemavzrd /usr/local/bin/schemavzrd
WORKDIR /app
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

EXPOSE 5174
ENV DB_URL="" OUTPUT_DIR="/app/out/schema"
CMD ["/usr/local/bin/entrypoint.sh"]

