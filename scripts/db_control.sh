#!/usr/bin/env bash
set -euo pipefail

# Add PostgreSQL bin to PATH if it exists
if [ -d "/usr/lib/postgresql/15/bin" ]; then
    export PATH="/usr/lib/postgresql/15/bin:$PATH"
fi

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# Configuration
POSTGRES_DATA="${POSTGRES_DATA:-$ROOT_DIR/.postgresql/data}"
POSTGRES_RUN_DIR="${POSTGRES_RUN_DIR:-$ROOT_DIR/.postgresql/run}"
LOG_FILE="${POSTGRES_LOG:-$POSTGRES_DATA/postgres.log}"

function show_help {
    echo "Usage: ./scripts/db_control.sh [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  start    Start the PostgreSQL server and run migrations"
    echo "  stop     Stop the PostgreSQL server"
    echo "  restart  Restart the PostgreSQL server"
    echo "  status   Show the status of the PostgreSQL server"
    echo "  reset    Reset the database (WARNING: DELETES ALL DATA)"
}

if [ -z "${1:-}" ]; then
    show_help
    exit 1
fi

function start_postgres {
    # Auto-initialize if data directory doesn't exist
    if [ ! -d "$POSTGRES_DATA" ] || [ ! -f "$POSTGRES_DATA/PG_VERSION" ]; then
        echo "PostgreSQL data directory not initialized. Initializing now..."
        mkdir -p "$POSTGRES_DATA"
        mkdir -p "$POSTGRES_RUN_DIR"
        initdb -D "$POSTGRES_DATA" --auth=trust -U postgres
        
        # Configure PostgreSQL to use our custom run directory
        echo "unix_socket_directories = '$POSTGRES_RUN_DIR'" >> "$POSTGRES_DATA/postgresql.conf"
        
        echo "PostgreSQL cluster initialized at $POSTGRES_DATA"
    else
        # Ensure socket directory configuration exists for existing installations
        if ! grep -q "^unix_socket_directories" "$POSTGRES_DATA/postgresql.conf"; then
            echo "Updating postgresql.conf with socket directory..."
            # Comment out the default setting and add our custom one
            sed -i.bak "s|^#unix_socket_directories.*|unix_socket_directories = '$POSTGRES_RUN_DIR'|" "$POSTGRES_DATA/postgresql.conf"
        fi
    fi
    
    # Ensure run directory exists
    mkdir -p "$POSTGRES_RUN_DIR"

    if pg_ctl -D "$POSTGRES_DATA" status >/dev/null 2>&1; then
        echo "PostgreSQL already running for data directory $POSTGRES_DATA"
        echo "Stopping existing server to apply configuration changes..."
        pg_ctl -D "$POSTGRES_DATA" stop -m fast
        sleep 2
    fi
    
    echo "Starting PostgreSQL server..."
    pg_ctl -D "$POSTGRES_DATA" -l "$LOG_FILE" -o "-k $POSTGRES_RUN_DIR" start
    echo "PostgreSQL started (log: $LOG_FILE)"

    echo "Waiting for PostgreSQL to be fully ready..."
    local max_retries=10
    local count=0
    while ! pg_ctl -D "$POSTGRES_DATA" status >/dev/null 2>&1; do
        if [ "$count" -ge "$max_retries" ]; then
            echo "Error: PostgreSQL did not start in time."
            exit 1
        fi
        echo "Still waiting..."
        sleep 1
        count=$((count + 1))
    done
    echo "PostgreSQL is ready."

    # Check if database exists
    if ! psql -h "$POSTGRES_RUN_DIR" -U postgres -lqt | cut -d \| -f 1 | grep -qw mul_in_one; then
        echo "Database 'mul_in_one' not found. Creating it..."
        createdb -h "$POSTGRES_RUN_DIR" -U postgres mul_in_one
    else
        echo "Database 'mul_in_one' already exists."
    fi

    echo "Running Alembic database migrations..."
    # Use uv if available, otherwise try direct alembic
    if command -v uv &> /dev/null; then
        (cd "$ROOT_DIR" && uv run alembic upgrade head)
    elif command -v alembic &> /dev/null; then
        (cd "$ROOT_DIR" && alembic upgrade head)
    else
        echo "Warning: Neither 'uv' nor 'alembic' command found. Skipping migrations."
        echo "Please run migrations manually: cd $ROOT_DIR && uv run alembic upgrade head"
    fi
    echo "Alembic migrations applied."
}

function stop_postgres {
    if ! pg_ctl -D "$POSTGRES_DATA" status >/dev/null 2>&1; then
        echo "PostgreSQL is not running."
        return 0
    fi

    echo "Stopping PostgreSQL server for data directory: $POSTGRES_DATA"
    pg_ctl -D "$POSTGRES_DATA" stop -m fast
    echo "PostgreSQL stopped."
}

function reset_postgres {
    echo "⚠️  WARNING: This will DELETE ALL DATA in PostgreSQL!"
    echo "Data directory: $POSTGRES_DATA"
    echo ""
    read -p "Are you sure you want to reset? Type 'yes' to confirm: " -r
    echo
    if [[ ! $REPLY =~ ^yes$ ]]; then
        echo "Aborting reset."
        exit 1
    fi

    echo "Resetting PostgreSQL cluster at $POSTGRES_DATA"
    
    # Stop if running
    if [ -d "$POSTGRES_DATA" ]; then
        if pg_ctl -D "$POSTGRES_DATA" status >/dev/null 2>&1; then
             echo "Stopping running PostgreSQL server..."
             pg_ctl -D "$POSTGRES_DATA" stop -m fast
        fi
        
        # Backup
        BACKUP_DIR="$ROOT_DIR/.postgresql/backups"
        mkdir -p "$BACKUP_DIR"
        TIMESTAMP=$(date +%Y%m%d_%H%M%S)
        BACKUP_NAME="backup_before_reset_$TIMESTAMP.tar.gz"
        echo "Creating backup: $BACKUP_DIR/$BACKUP_NAME"
        # Check if data directory is not empty before backing up
        if [ "$(ls -A $POSTGRES_DATA)" ]; then
             tar -czf "$BACKUP_DIR/$BACKUP_NAME" -C "$ROOT_DIR/.postgresql" data 2>/dev/null || echo "Backup warning."
        fi

        echo "Removing existing data directory"
        rm -rf "$POSTGRES_DATA"
    fi

    mkdir -p "$POSTGRES_DATA"
    echo "Initializing new PostgreSQL cluster..."
    mkdir -p "$POSTGRES_RUN_DIR"
    initdb -D "$POSTGRES_DATA" --auth=trust -U postgres
    
    # Configure PostgreSQL to use our custom run directory
    echo "unix_socket_directories = '$POSTGRES_RUN_DIR'" >> "$POSTGRES_DATA/postgresql.conf"

    echo "Temporarily starting server to create database..."
    pg_ctl -D "$POSTGRES_DATA" -l "$POSTGRES_DATA/postgres_reset.log" start

    # Wait for server
    local max_retries=5
    local count=0
    while ! pg_ctl -D "$POSTGRES_DATA" status >/dev/null 2>&1; do
        if [ "$count" -ge "$max_retries" ]; then
             echo "Error: Temporary server failed to start."
             exit 1
        fi
        sleep 1
        count=$((count + 1))
    done

    echo "Creating application database 'mul_in_one'..."
    createdb -h "$POSTGRES_RUN_DIR" -U postgres mul_in_one

    echo "Stopping temporary server..."
    pg_ctl -D "$POSTGRES_DATA" stop -m fast

    echo "PostgreSQL reset complete. Run './scripts/db_control.sh start' to launch."
}

case "$1" in
    start)
        start_postgres
        ;;
    stop)
        stop_postgres
        ;;
    restart)
        echo "Restarting PostgreSQL services..."
        stop_postgres
        start_postgres
        ;;
    status)
        if [ ! -d "$POSTGRES_DATA" ]; then
             echo "Data directory not found."
             exit 1
        fi
        pg_ctl -D "$POSTGRES_DATA" status
        ;;
    reset)
        reset_postgres
        ;;
    *)
        echo "Unknown command: $1"
        show_help
        exit 1
        ;;
esac
