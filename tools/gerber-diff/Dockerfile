FROM debian:bookworm-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    gerbv \
    python3 \
    python3-numpy \
    python3-pil \
    && rm -rf /var/lib/apt/lists/*

# Run as the same uid/gid docker build was invoked with (defaults to 1000,
# a typical single-user Linux workstation uid) so output files land owned
# by the host user instead of root. Override at build time if your uid
# differs: docker build --build-arg UID=$(id -u) --build-arg GID=$(id -g) ...
ARG UID=1000
ARG GID=1000
RUN groupadd -g "$GID" worker && useradd -u "$UID" -g "$GID" -m worker
USER worker

WORKDIR /work
ENTRYPOINT ["python3"]
