#!/bin/sh
uvicorn api:app --host 127.0.0.1 --port 8000 &
sleep 8
streamlit run dashboard.py --server.port ${PORT:-8501} --server.address 0.0.0.0 --server.headless true --server.enableCORS false --server.enableXsrfProtection false