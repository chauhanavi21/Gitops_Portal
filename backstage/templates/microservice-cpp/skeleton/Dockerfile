FROM gcc:13 AS builder
WORKDIR /app
COPY . .
RUN mkdir build && cd build && \
    cmake .. -DCMAKE_BUILD_TYPE=Release && \
    cmake --build . --parallel $(nproc)

FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/* && \
    groupadd -r appgroup && useradd -r -g appgroup appuser
COPY --from=builder /app/build/${{ values.name }} /usr/local/bin/service
USER appuser
EXPOSE ${{ values.port }}
HEALTHCHECK --interval=10s --timeout=3s CMD curl -f http://localhost:${{ values.port }}/healthz || exit 1
ENTRYPOINT ["service"]
