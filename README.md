# Polymarket Alpha Finder

A Python web application that takes a Polymarket market URL, discovers all wallets that traded in that market, analyzes their full trading history across all of Polymarket, classifies them (Whale Gambler / Scalper / Systematic), and scores them 0–100.
<img width="1872" height="1167" alt="image" src="https://github.com/user-attachments/assets/f9d3e6c0-4e09-4162-82f5-7c2be17060ef" />


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
