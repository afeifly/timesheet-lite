# Deployment Guide

## Prerequisites
- **Python 3.8+**
- **Node.js 16+**
- **Caddy** (Web Server)

## 1. Backend Setup

1.  Navigate to the backend directory:
    ```bash
    cd backend
    ```
2.  Create and activate virtual environment:
    ```bash
    python -m venv .venv
    source .venv/bin/activate
    ```
3.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
4.  Run the backend (it will listen on `0.0.0.0:8003`):
    ```bash
    python run.py
    ```
    *Note: For production, use a process manager like `supervisor` or `systemd`.*

## 2. Frontend Setup

1.  Navigate to the frontend directory:
    ```bash
    cd frontend
    ```
2.  Install dependencies:
    ```bash
    npm install
    ```
3.  Build the project:
    ```bash
    npm run build
    ```
    This creates the `dist` folder.

## 3. Caddy Setup (Reverse Proxy)

1.  Ensure you have `Caddyfile` in the project root.
2.  Run Caddy from the project root:
    ```bash
    caddy run
    ```
    Or to run in background:
    ```bash
    caddy start
    ```

## 4. Access

- Open your browser and go to `http://localhost` (or your server's IP/domain).
- The frontend will be served, and API requests to `/api/...` will be proxied to the backend.
