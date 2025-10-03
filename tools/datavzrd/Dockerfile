# syntax=docker/dockerfile:1
FROM rust:1.82-bookworm AS build

RUN apt-get update && apt-get install -y --no-install-recommends pkg-config libssl-dev ca-certificates python3 && rm -rf /var/lib/apt/lists/*

RUN cargo install datavzrd --locked || cargo install datavzrd

FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates python3 && rm -rf /var/lib/apt/lists/*
COPY --from=build /usr/local/cargo/bin/datavzrd /usr/local/bin/datavzrd
WORKDIR /app
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

EXPOSE 5173
ENV VIZ_FILE=""
CMD ["/usr/local/bin/entrypoint.sh"]
