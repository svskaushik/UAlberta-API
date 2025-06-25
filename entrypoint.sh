#!/bin/sh
exec python -m uvicorn main:app --host "${API_HOST:-0.0.0.0}" --port "${API_PORT:-8000}"
