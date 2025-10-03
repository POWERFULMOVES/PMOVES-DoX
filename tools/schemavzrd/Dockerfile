FROM rust:1.84-bookworm AS build
RUN apt-get update && apt-get install -y --no-install-recommends \
    git build-essential pkg-config libssl-dev ca-certificates \
    nodejs npm \
    && rm -rf /var/lib/apt/lists/*
# schemavzrd build.rs invokes webpack; install CLI globally
RUN npm install -g webpack webpack-cli
# schemavzrd is not published on crates.io; install from GitHub
RUN cargo install --git https://github.com/datavzrd/schemavzrd --bin schemavzrd

FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates python3 && rm -rf /var/lib/apt/lists/*
COPY --from=build /usr/local/cargo/bin/schemavzrd /usr/local/bin/schemavzrd
WORKDIR /app
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

EXPOSE 5174
ENV DB_URL="" OUTPUT_DIR="/app/out/schema"
CMD ["/usr/local/bin/entrypoint.sh"]
