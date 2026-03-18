# Polymarket Alpha Finder

A tool to discover and analyze top Polymarket traders, score wallets by win rate, diversification, and strategy.

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Run the server:
   ```bash
   python -m uvicorn app:app --host 0.0.0.0 --port 8000
   ```

3. Open `http://localhost:8000` in your browser.

## Deployment

To deploy this application, you can use any service that supports Python FastAPI applications (e.g., Render, Railway, DigitalOcean).

For a VPS deployment (Ubuntu):
1. Install Python, pip, and nginx.
2. Clone this repository.
3. Install requirements.
4. Run the app using `gunicorn`:
   ```bash
   gunicorn app:app -w 4 -k uvicorn.workers.UvicornWorker -b 127.0.0.1:8000
   ```
5. Configure Nginx to reverse proxy port 80/443 to `127.0.0.1:8000`.
