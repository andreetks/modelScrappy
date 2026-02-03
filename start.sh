#!/usr/bin/env bash
set -x
echo "PORT is: $PORT"
ls -la
python -V
pip list | head -20
uvicorn api:app --host 0.0.0.0 --port $PORT --log-level debug
