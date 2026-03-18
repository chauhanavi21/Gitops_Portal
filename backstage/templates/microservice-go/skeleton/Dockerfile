FROM golang:${{ values.goVersion }}-alpine AS builder
WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -ldflags="-s -w" -o /app/service .

FROM alpine:3.19
RUN apk --no-cache add ca-certificates curl && \
    addgroup -S appgroup && adduser -S appuser -G appgroup
COPY --from=builder /app/service /usr/local/bin/service
USER appuser
EXPOSE ${{ values.port }}
HEALTHCHECK --interval=10s --timeout=3s CMD curl -f http://localhost:${{ values.port }}/healthz || exit 1
ENTRYPOINT ["service"]
