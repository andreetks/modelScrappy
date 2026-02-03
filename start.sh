#!/usr/bin/env bash
# Make sure to use the PORT environment variable provided by Render
# Logs are enabled for debugging
uvicorn api:app --host 0.0.0.0 --port $PORT --log-level info
