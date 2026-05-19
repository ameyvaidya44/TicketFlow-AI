#!/usr/bin/env bash
# build.sh — Render build script for TicketFlow AI backend
# Set this as your Build Command in the Render dashboard.
set -e

echo "==> Installing CPU-only PyTorch (avoids 2GB CUDA build)..."
pip install torch==2.3.0+cpu --index-url https://download.pytorch.org/whl/cpu

echo "==> Installing remaining dependencies..."
pip install -r requirements.txt

echo "==> Downloading spaCy language model..."
python -m spacy download en_core_web_sm

echo "==> Training ML models..."
python ml/train.py

echo "==> Build complete."
