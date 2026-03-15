#!/bin/bash
set -e

echo "🚀 Setting up environment for Coffee Price IE..."

# 1. Check Python version
python3 --version || { echo "❌ Python 3 is not installed. Please install Python 3.9+"; exit 1; }

# 2. Create virtual environment (optional but recommended)
echo "📦 Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate || source venv/Scripts/activate

# 3. Upgrade pip
echo "🆙 Upgrading pip..."
pip install --upgrade pip

# 4. Install base requirements
echo "📥 Installing base requirements..."
pip install -r requirements.txt

# 5. Install Kaggle-specific dependencies that were missing from requirements.txt
echo "📥 Installing ML and scraping dependencies (Transformers, Trafilatura, Underthesea, etc.)..."
pip install trafilatura bs4 underthesea huggingface_hub
pip install transformers accelerate bitsandbytes torch

# 6. Create required directory structure
echo "📁 Creating data directories..."
mkdir -p data/01_discovered
mkdir -p data/02_raw_articles
mkdir -p data/03_articles
mkdir -p data/04_price_mentions
mkdir -p data/05_disagreement
mkdir -p data/06_ground_truth
mkdir -p data/07_exports

echo "⚠️ IMPORTANT: Please ensure your source data (.jsonl files) is placed in data/02_raw_articles/ before running the pipeline."

echo "✅ Setup complete! You can now run the pipeline using:"
echo "python runner.py --model qwen"
echo "If you use Llama, remember to export your Hugging Face Token: export HF_TOKEN='your_token'"
