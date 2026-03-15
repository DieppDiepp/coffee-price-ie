import os
import shutil
import argparse
import subprocess

def run_command(command, description):
    print(f"\n🚀 {description}")
    print(f"Executing: {command}")
    try:
        subprocess.run(command, shell=True, check=True)
        print("✅ Success!")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error executing command: {e}")
        exit(1)

def main():
    parser = argparse.ArgumentParser(description="Run the Coffee Price IE Pipeline")
    parser.add_argument("--model", type=str, choices=["qwen", "llama"], default="qwen", 
                        help="Model to use for Information Extraction (default: qwen)")
    parser.add_argument("--skip-parser", action="store_true", help="Skip the parsing step")
    parser.add_argument("--skip-ie", action="store_true", help="Skip the IE step")
    parser.add_argument("--skip-disagreement", action="store_true", help="Skip the disagreement modeling step")
    
    args = parser.parse_args()

    # Create necessary data directories if they don't exist
    directories = [
        "data/01_discovered",
        "data/02_raw_articles",
        "data/03_articles",
        "data/04_price_mentions",
        "data/05_disagreement"
    ]
    for directory in directories:
        os.makedirs(directory, exist_ok=True)

    print("☕ Starting Coffee Price IE Pipeline Runner ☕")
    
    # 0. Check data dependencies
    if not args.skip_parser:
        raw_data_exists = any(fname.endswith('.jsonl') for fname in os.listdir("data/02_raw_articles")) if os.path.exists("data/02_raw_articles") else False
        if not raw_data_exists:
            print("⚠️ WARNING: No .jsonl files found in data/02_raw_articles/. Step 03_parser requires raw HTML data.")
            print("Please ensure your scraped source data is placed in data/02_raw_articles/ before running.")
    
    # 1. Parser
    if not args.skip_parser:
        run_command("python pipeline/03_parser/main.py", "Step 03: Parser (HTML Processing & Sentence Splitting)")
    
    # 2. Information Extraction
    if not args.skip_ie:
        ie_cmd = f"python pipeline/04_ie/main.py --model {args.model}"
        # If Llama is selected, ensure HF_TOKEN is available
        if args.model == "llama" and not os.environ.get("HF_TOKEN"):
            print("⚠️ WARNING: HF_TOKEN environment variable is not set. Llama 3.1 may fail to load if it's a gated model.")
            print("Set it using: export HF_TOKEN='your_token_here'")
        
        run_command(ie_cmd, f"Step 04: Information Extraction using {args.model.upper()}")
        
    # 3. Disagreement Modeling
    if not args.skip_disagreement:
        run_command("python pipeline/05_disagreement/main.py", "Step 05: Disagreement Modeling (PhoBERT)")

    print("\n🎉 Pipeline execution completed successfully! Check the /data directory for outputs.")

if __name__ == "__main__":
    main()