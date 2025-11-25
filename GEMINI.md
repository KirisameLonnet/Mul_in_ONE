# GEMINI Project Context

## Project Overview

This project, "Mul-in-One," is a multi-agent chat service built on the NVIDIA NeMo Agent Toolkit. It supports both a web-based interface and a command-line interface (CLI) for creating and participating in conversations with multiple AI agents. The system is designed with a backend service that handles the core logic of the multi-agent conversations, and a frontend for user interaction.

The core of the project is the ability to have multiple AI agents interact with each other in a group chat setting. These agents can be customized with different personas and can be configured to use different large language models (LLMs). The project also includes a persistence layer to save and retrieve conversation histories.

## Technology Stack

*   **Backend**: Python, FastAPI, SQLAlchemy
*   **Frontend**: Vue.js, Vite
*   **AI**: NVIDIA NeMo Agent Toolkit
*   **Database**: PostgreSQL with Alembic for migrations
*   **Package Management**: `uv` for Python, `npm` for the frontend

## Project Structure

The project is organized into several key directories:

*   `src/mul_in_one_nemo`: The main Python package for the backend service and CLI.
    *   `service/`: Contains the FastAPI application, including API endpoints for managing sessions and personas.
    *   `db/`: Defines the database schema and provides an interface for interacting with the database.
    *   `memory/`: Manages the conversation history and memory for the AI agents.
    *   `runtime.py`: The core logic for running the multi-agent chat.
    *   `scheduler.py`: Determines which agent should speak next.
*   `src/mio_frontend/mio-frontend`: The Vue.js frontend application.
*   `alembic/`: Contains the database migration scripts.
*   `personas/`: Configuration files for the AI agent personas.
*   `scripts/`: Utility scripts for managing the development environment (e.g., starting the database).

## Building and Running the Project

### Prerequisites

*   Python 3.11+
*   `uv` (Python package manager)
*   Node.js and `npm`
*   Docker

### 1. Initial Setup

1.  **Clone the repository.**
2.  **Set up the Python environment:**
    ```bash
    uv venv .venv
    source .venv/bin/activate
    ```
3.  **Install dependencies:**
    ```bash
    ./scripts/bootstrap_toolkit.sh
    ```

### 2. Database

1.  **Start the PostgreSQL database:**
    ```bash
    ./scripts/db_start.sh
    ```
2.  **Run database migrations:**
    ```bash
    alembic upgrade head
    ```

### 3. Backend

*   **Run the FastAPI server:**
    ```bash
    uvicorn mul_in_one_nemo.service.main:app --reload
    ```
    The server will be available at `http://127.0.0.1:8000`.

### 4. Frontend

1.  **Navigate to the frontend directory:**
    ```bash
    cd src/mio_frontend/mio-frontend
    ```
2.  **Install dependencies:**
    ```bash
    npm install
    ```
3.  **Start the development server:**
    ```bash
    npm run dev
    ```
    The frontend will be available at `http://localhost:5173`.

### 5. CLI

*   To run the CLI application:
    ```bash
    uv run mul-in-one-nemo --stream
    ```

## Development Conventions

*   **Backend**: The backend code follows standard Python conventions and uses FastAPI for the web framework. Database interactions are handled through SQLAlchemy.
*   **Frontend**: The frontend is a standard Vue.js application built with Vite.
*   **Testing**: The project uses `pytest` for testing. Tests are located in the `tests/` directory. To run the tests, use the `pytest` command.
*   **Configuration**: The application is configured through environment variables and YAML files in the `personas/` directory. The `.envrc` file is used to manage environment variables for development.
