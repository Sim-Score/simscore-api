#!/bin/bash

echo "Running verified user tests..."
poetry run pytest tests/integration/test_auth_verified.py -v -s
echo "Waiting for rate limit reset..."
sleep 61

echo "Running guest user tests..."
poetry run pytest tests/integration/test_auth_guest.py -v -s
echo "Waiting for rate limit reset..."
sleep 61

echo "Running rate limit tests..."
poetry run pytest tests/integration/test_auth_basic.py -v -s 