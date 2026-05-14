"""
llm_client.py — OpenAI-compatible client (supports OpenAI, DeepSeek, etc.)
"""
import json
import os
import sys
from pathlib import Path

# Load .env from same directory
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent / ".env")
except ImportError:
    pass  # fallback to env vars

from extraction_config import PROVIDERS, MAX_TOKENS_OUT
from prompts import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE


def init_client(provider="openai"):
    """
    Initialize OpenAI-compatible client.

    Providers:
      - "openai"   → gpt-4o-mini (needs OPENAI_API_KEY)
      - "deepseek" → deepseek-chat (needs DEEPSEEK_API_KEY)
      - Custom: set OPENAI_API_KEY + OPENAI_BASE_URL env vars
    """
    try:
        from openai import OpenAI
    except ImportError:
        print("ERROR: pip install openai")
        sys.exit(1)

    preset = PROVIDERS.get(provider)
    if preset:
        api_key  = os.environ.get(preset["env_key"])
        base_url = preset["base_url"]
        model    = preset["model"]
        if not api_key:
            print(f"ERROR: export {preset['env_key']}='...'")
            sys.exit(1)
    else:
        # Fallback: dùng env vars trực tiếp
        api_key  = os.environ.get("OPENAI_API_KEY")
        base_url = os.environ.get("OPENAI_BASE_URL")
        model    = provider  # provider name = model name
        if not api_key:
            print("ERROR: export OPENAI_API_KEY='...'")
            sys.exit(1)

    client = OpenAI(api_key=api_key, base_url=base_url)
    print(f"  Client: provider={provider}, model={model}")
    if base_url:
        print(f"  Base URL: {base_url}")
    return client, model


def extract_one(client, model, title, snippet, pub_date, content):
    """
    Call LLM to extract structured info from 1 article.
    Returns dict with extracted fields + _status + _tokens_used.
    """
    user_msg = USER_PROMPT_TEMPLATE.format(
        title=title,
        snippet=snippet,
        pub_date=pub_date,
        content=content,
    )

    fallback = {
        "is_coffee_price": False,
        "direction": "NONE",
        "price_vnd": None,
        "price_change": None,
        "certainty": 5,
        "content_date": None,
    }

    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": user_msg},
            ],
            max_tokens=MAX_TOKENS_OUT,
            temperature=0.0,
            response_format={"type": "json_object"},
            extra_body={"thinking": {"type": "disabled"}},
        )
        raw = resp.choices[0].message.content or ""
        raw = raw.strip()

        # Handle markdown code blocks
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]

        result = json.loads(raw)
        result["_status"] = "ok"
        result["_tokens_used"] = (
            resp.usage.total_tokens if resp.usage else 0
        )
        return result

    except json.JSONDecodeError:
        fallback["_status"] = "json_error"
        fallback["_tokens_used"] = 0
        return fallback

    except Exception as e:
        fallback["_status"] = f"error:{str(e)[:80]}"
        fallback["_tokens_used"] = 0
        return fallback
