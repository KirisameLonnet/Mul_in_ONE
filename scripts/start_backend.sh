#!/usr/bin/env bash
set -euo pipefail

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# Parse arguments
USE_SYSTEMD=false
while [[ $# -gt 0 ]]; do
    case $1 in
        -d|--daemon)
            USE_SYSTEMD=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [-d|--daemon]"
            exit 1
            ;;
    esac
done

cd "$ROOT_DIR"

# Ensure we are in repo root and env files exist
if [[ ! -f "$ROOT_DIR/.envrc" ]]; then
    echo "Error: .envrc not found in $ROOT_DIR"
    echo "Hint: run from repo root or create the env file."
    exit 1
fi

# Activate venv if present, else warn
if [[ -d "$ROOT_DIR/.venv" ]]; then
    # shellcheck disable=SC1091
    source "$ROOT_DIR/.venv/bin/activate"
else
    echo "Warning: .venv not found. You can create it with:"
    echo "  uv venv && source .venv/bin/activate && uv sync"
fi

# Load environment variables using direnv or nix-shell
if command -v direnv >/dev/null 2>&1; then
    eval "$(direnv export bash)"
elif command -v nix-shell >/dev/null 2>&1; then
    # If direnv is not available, use nix-shell
    exec nix-shell --run "$(printf '%q ' "$0" "$@")"
else
    echo "Warning: Neither direnv nor nix-shell found. Environment may be incomplete."
    # Try to source .envrc as fallback (will fail on 'use flake' but continue)
    source "$ROOT_DIR/.envrc" 2>/dev/null || true
fi

# Check if Milvus is running
check_milvus() {
    echo "Checking Milvus connection..."
    
    # Check if port 19530 is open
    if command -v nc >/dev/null 2>&1; then
        if nc -z localhost 19530 2>/dev/null; then
            echo "✓ Milvus is running on port 19530"
            return 0
        fi
    fi
    
    echo "⚠️  Warning: Cannot connect to Milvus on port 19530"
    echo "   The backend will fail to start without Milvus."
    echo ""
    echo "   To start Milvus, run:"
    echo "   ./scripts/milvus_control.sh start"
    echo ""
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Aborted."
        exit 1
    fi
}

check_milvus

# If daemon mode, create and start systemd service
if [[ "$USE_SYSTEMD" == true ]]; then
    SERVICE_NAME="mul-in-one-backend"
    SERVICE_FILE="$HOME/.config/systemd/user/$SERVICE_NAME.service"
    
    echo "Creating systemd user service..."
    mkdir -p "$HOME/.config/systemd/user"
    
    cat > "$SERVICE_FILE" <<EOF
[Unit]
Description=Mul-in-One Backend Server
After=network.target

[Service]
Type=simple
WorkingDirectory=$ROOT_DIR
Environment="PATH=$ROOT_DIR/.venv/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=$ROOT_DIR/.venv/bin/uvicorn mul_in_one_nemo.service.app:create_app --host 0.0.0.0 --port 8000 --reload --reload-dir src --reload-dir configs
Restart=on-failure
RestartSec=10
StandardOutput=append:$ROOT_DIR/logs/backend.log
StandardError=append:$ROOT_DIR/logs/backend-error.log

[Install]
WantedBy=default.target
EOF

    # Load environment variables into the service file
    if [[ -f "$ROOT_DIR/.envrc" ]]; then
        echo "Loading environment variables into service..."
        while IFS= read -r line; do
            # Skip comments and empty lines
            [[ "$line" =~ ^#.*$ || -z "$line" ]] && continue
            # Extract export statements
            if [[ "$line" =~ ^export[[:space:]]+([^=]+)=(.+)$ ]]; then
                var_name="${BASH_REMATCH[1]}"
                var_value="${BASH_REMATCH[2]}"
                # Remove quotes and evaluate $(pwd)
                var_value=$(eval echo "$var_value")
                echo "Environment=\"$var_name=$var_value\"" >> "$SERVICE_FILE.tmp"
            fi
        done < "$ROOT_DIR/.envrc"
        
        # Insert environment variables after [Service]
        sed -i '/^\[Service\]$/r '"$SERVICE_FILE.tmp" "$SERVICE_FILE"
        rm -f "$SERVICE_FILE.tmp"
    fi
    
    # Reload systemd and start service
    systemctl --user daemon-reload
    systemctl --user enable "$SERVICE_NAME"
    systemctl --user restart "$SERVICE_NAME"
    
    echo "✓ Backend service started as systemd daemon"
    echo "  Status: systemctl --user status $SERVICE_NAME"
    echo "  Logs:   journalctl --user -u $SERVICE_NAME -f"
    echo "  Stop:   systemctl --user stop $SERVICE_NAME"
    exit 0
fi

echo "Starting FastAPI backend server..."
echo "API will be available at: http://localhost:8000"
echo ""

# Start uvicorn with reload, using whitelist to avoid permission issues
ARGS=("--host" "0.0.0.0" "--port" "8000")

# Enable reload unless BACKEND_NO_RELOAD is set
if [[ -z "${BACKEND_NO_RELOAD:-}" ]]; then
    ARGS+=("--reload")
    # Use whitelist approach: only watch source and config directories
    ARGS+=("--reload-dir" "src")
    ARGS+=("--reload-dir" "configs")
fi

uv run uvicorn mul_in_one_nemo.service.app:create_app "${ARGS[@]}"
