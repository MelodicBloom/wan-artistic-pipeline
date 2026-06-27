#!/usr/bin/env bash
# ============================================================
# wan-artistic-pipeline — dependency installer
# Run once after cloning:
#   chmod +x setup.sh && ./setup.sh
# ============================================================
set -e

echo "=== Wan Artistic Pipeline — Setup ==="

# --- Python version check ---
PYTHON=$(python3 -c 'import sys; print(sys.version_info >= (3,10))' 2>/dev/null)
if [ "$PYTHON" != "True" ]; then
  echo "ERROR: Python 3.10+ required"
  exit 1
fi
echo "✓ Python OK"

# --- Virtual environment ---
if [ ! -d ".venv" ]; then
  python3 -m venv .venv
  echo "✓ Virtual environment created at .venv/"
fi
source .venv/bin/activate

# --- Upgrade pip ---
pip install --upgrade pip --quiet

# --- Core deps ---
echo "--- Installing core dependencies ---"
pip install \
  torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121 \
  --quiet

pip install \
  transformers>=4.40.0 \
  Pillow>=10.0.0 \
  requests>=2.31.0 \
  pyyaml>=6.0 \
  python-dotenv>=1.0.0 \
  watchdog>=4.0.0 \
  tqdm>=4.66.0 \
  ruff \
  --quiet

# --- CLIP ---
echo "--- Installing CLIP ---"
pip install openai-clip --quiet

# --- Optional: Dashscope (Qwen prompt extension) ---
read -p "Install Dashscope (Qwen prompt extension)? [y/N] " DASH
if [[ "$DASH" =~ ^[Yy]$ ]]; then
  pip install dashscope>=1.14.0 --quiet
  echo "✓ Dashscope installed"
fi

# --- Optional: OpenAI (caption fallback) ---
read -p "Install OpenAI SDK (captioning fallback)? [y/N] " OAI
if [[ "$OAI" =~ ^[Yy]$ ]]; then
  pip install openai>=1.30.0 --quiet
  echo "✓ OpenAI SDK installed"
fi

# --- Optional: flash-attn ---
read -p "Install flash-attn (optional, may take 5-10 min to build)? [y/N] " FA
if [[ "$FA" =~ ^[Yy]$ ]]; then
  pip install flash-attn --no-build-isolation --quiet && echo "✓ flash-attn installed" || echo "⚠ flash-attn failed — model falls back to standard attention automatically"
fi

# --- Env file ---
if [ ! -f ".env" ]; then
  cp .env.example .env
  echo "✓ .env created from .env.example — fill in your tokens"
else
  echo "✓ .env already exists"
fi

# --- Input / output dirs ---
mkdir -p input outputs

echo ""
echo "=== Setup complete ==="
echo "  Activate env:  source .venv/bin/activate"
echo "  Dry run:       python generate.py --dry-run"
echo "  Full run:      python generate.py"
echo "  Watch mode:    python generate.py --watch"
