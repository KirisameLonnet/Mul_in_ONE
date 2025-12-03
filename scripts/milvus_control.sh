#!/usr/bin/env bash

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# Assuming the script is in PROJECT_ROOT/scripts/, the project root is one level up
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Set the path to the Milvus docker-compose file using the absolute path
# Keep vendor assets untouched by using the project-level override compose
MILVUS_COMPOSE_FILE="$PROJECT_ROOT/configs/docker-compose.milvus.local.yml"
# 注意：不要放在 git 子模块中，应该放在项目根目录
: "${DOCKER_VOLUME_DIRECTORY:="$PROJECT_ROOT/.docker-volumes"}"
export MILVUS_CONFIG_PATH="$PROJECT_ROOT/configs/milvus.yaml"
export MILVUS_CONFIG_DIR="$PROJECT_ROOT/configs"
export DOCKER_VOLUME_DIRECTORY
: "${DOCKER_NETWORK_NAME:=nvidia-rag-test}"

ensure_network() {
    if ! docker network inspect "$DOCKER_NETWORK_NAME" >/dev/null 2>&1; then
        echo "Creating docker network: $DOCKER_NETWORK_NAME"
        docker network create "$DOCKER_NETWORK_NAME"
    fi
}

# Check and fix Milvus config directory issue
fix_milvus_config() {
    local config_path="$PROJECT_ROOT/configs/milvus.yaml"
    
    # If milvus.yaml exists as a directory, remove it
    if [ -d "$config_path" ]; then
        echo "⚠️  Warning: Found milvus.yaml as a directory instead of a file"
        echo "   Removing empty directory: $config_path"
        rmdir "$config_path" 2>/dev/null || {
            echo "   Directory not empty, backing up to milvus.yaml.bak/"
            mv "$config_path" "${config_path}.bak"
        }
    fi
    
    # Note: We don't create a config file since Milvus uses default config
    # The docker-compose.yml has been updated to not require --config flag
}

# Check if the file exists
if [ ! -f "$MILVUS_COMPOSE_FILE" ]; then
    echo "Error: Could not find the Milvus docker-compose file at: $MILVUS_COMPOSE_FILE"
    exit 1
fi

# Run config fix before any operations
fix_milvus_config

function show_help {
    echo "Usage: ./scripts/milvus_control.sh [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  start    Start the Milvus services in detached mode"
    echo "  stop     Stop and remove the Milvus containers"
    echo "  restart  Restart the Milvus services"
    echo "  status   Show the status of Milvus containers"
    echo "  logs     Follow the logs of Milvus containers"
}

if [ -z "$1" ]; then
    show_help
    exit 1
fi

case "$1" in
    start)
        echo "Starting Milvus services..."
        ensure_network
        docker compose -f "$MILVUS_COMPOSE_FILE" up -d
        if [ $? -eq 0 ]; then
            echo "Milvus services started successfully."
        else
            echo "Failed to start Milvus services."
        fi
        ;;
    stop)
        echo "Stopping Milvus services..."
        docker compose -f "$MILVUS_COMPOSE_FILE" down
        ;;
    restart)
        echo "Restarting Milvus services..."
        ensure_network
        docker compose -f "$MILVUS_COMPOSE_FILE" down && \
        docker compose -f "$MILVUS_COMPOSE_FILE" up -d
        ;;
    status)
        docker compose -f "$MILVUS_COMPOSE_FILE" ps
        ;;
    logs)
        docker compose -f "$MILVUS_COMPOSE_FILE" logs -f
        ;;
    *)
        echo "Unknown command: $1"
        show_help
        exit 1
        ;;
esac
