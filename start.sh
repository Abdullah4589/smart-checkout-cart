#!/bin/sh
exec uvicorn main:app --app-dir backend --host 0.0.0.0 --port "$PORT"
