compose_file="${COMPOSE_FILE:-docker-compose.yml}"
docker compose -f "$compose_file" exec signal-api curl -s -X GET 'http://localhost:8080/v1/qrcodelink?device_name=glucose-alerts' --output /tmp/signal-qr.png
docker compose -f "$compose_file" cp signal-api:/tmp/signal-qr.png ./signal-qr.png
