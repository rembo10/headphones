# Headphones Docker Setup

This guide helps you run Headphones in Docker and Docker Compose.

## Quick Start with Docker Compose

The easiest way to get started is with Docker Compose:

```bash
docker-compose up -d
```

This will:
- Build the Docker image from the Dockerfile
- Start the Headphones container
- Create a persistent data volume for configuration and database
- Expose the web interface on port 8181

Access the web interface at: http://localhost:8181

## Stopping and Removing

```bash
# Stop the container
docker-compose stop

# Remove the container
docker-compose down

# Remove the container and volumes (WARNING: deletes data)
docker-compose down -v
```

## Manual Docker Commands

If you prefer to use Docker directly without Compose:

### Build the image

```bash
docker build -t headphones:latest .
```

### Run the container

```bash
docker run -d \
  --name headphones \
  -p 8181:8181 \
  -v headphones_data:/data \
  --restart unless-stopped \
  headphones:latest
```

## Configuration

### Accessing Configuration

The configuration file (`config.ini`) and database (`headphones.db`) are stored in the `/data` directory inside the container.

### Environment Variables

- `TZ`: Set the timezone (default: UTC). Example: `TZ=America/New_York`

### Volume Mounts

In `docker-compose.yml`, you can add additional volume mounts:

```yaml
volumes:
  - headphones_data:/data          # For config and database
  - /path/to/music:/music          # Your music library (optional)
  - /path/to/downloads:/downloads  # Downloads folder (optional)
```

## Port Configuration

The default port is `8181`. To use a different port, modify the port mapping in `docker-compose.yml`:

```yaml
ports:
  - "8888:8181"  # Maps host port 8888 to container port 8181
```

Then access at: http://localhost:8888

## Network

### Bridge Network

By default, Docker Compose creates a bridge network. To use the default bridge network:

```yaml
networks:
  default:
    driver: bridge
```

### Custom Network

To use a custom network for multiple services:

```yaml
networks:
  media-network:
    driver: bridge

services:
  headphones:
    networks:
      - media-network
```

## Troubleshooting

### View logs

```bash
docker-compose logs -f headphones
```

Or with direct Docker:

```bash
docker logs -f headphones
```

### Container won't start

Check the logs to see error messages:

```bash
docker-compose logs headphones
```

Common issues:
- Port 8181 is already in use
- Data directory permissions issue
- Missing dependencies

### Reset Configuration

If you want to start fresh with a clean configuration:

```bash
docker-compose down -v
docker-compose up -d
```

This removes the data volume, so a fresh `config.ini` will be created on startup.

## Performance Optimization

### Memory Limits

Add memory limits in `docker-compose.yml`:

```yaml
deploy:
  resources:
    limits:
      memory: 512M
      cpus: "1.0"
    reservations:
      memory: 256M
      cpus: "0.5"
```

### CPU Limits

Adjust CPU allocation as needed for your system.

## Integration with Other Services

### With Transmission (Torrent)

```yaml
services:
  headphones:
    # ... existing config ...
    depends_on:
      - transmission
    networks:
      - media-network

  transmission:
    image: transmissionbt/transmission:latest
    networks:
      - media-network
    ports:
      - "6969:6969"
      - "6969:6969/udp"
      - "9091:9091"
    volumes:
      - transmission_data:/config
      - /path/to/downloads:/downloads

volumes:
  headphones_data:
  transmission_data:

networks:
  media-network:
    driver: bridge
```

Configure Headphones to connect to Transmission at: `transmission:6969` (using the service name as hostname)

## Security Considerations

1. Change the default port if running on a public network
2. Use HTTPS in production (configure through Headphones settings)
3. The container runs as a non-root user (`headphones`) for security
4. Consider using a reverse proxy (nginx, Traefik) in production
5. Keep the Docker image updated regularly

## Updates

To update to the latest version:

```bash
docker-compose down
git pull origin master
docker-compose up -d --build
```

This will rebuild the image and start the updated container.
