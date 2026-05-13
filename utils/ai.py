from json import dump, loads
from math import ceil
from os import getenv, path

from dotenv import load_dotenv
from tqdm import tqdm

from utils.logger import logger

load_dotenv()

DEFAULT_MODEL = "gpt-5.4-mini"
DEFAULT_REASONING_EFFORT = "low"
DEFAULT_TIMEOUT_SECONDS = 120
DEFAULT_MAX_RETRIES = 3
DEFAULT_MAX_INPUT_TOKENS = 180000
DEFAULT_LANGUAGE = "italian"
PROMPT_CACHE_KEY = "flashfacts-facts-v1"
TOKEN_CHAR_RATIO = 3
TOKEN_WORD_RATIO = 1.5

FACTS_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "facts": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "body": {"type": "string"},
                },
                "required": ["title", "body"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["summary", "facts"],
    "additionalProperties": False,
}


class OpenAIConfigurationError(RuntimeError): ...


def get_int_env(name, default):
    value = getenv(name)
    if not value:
        return default
    try:
        return int(value)
    except ValueError:
        logger.warning(f"{name} must be an integer; using {default}")
        return default


def get_openai_client():
    api_key = getenv("OPENAI_API_KEY")
    if not api_key:
        raise OpenAIConfigurationError("OPENAI_API_KEY is required")

    try:
        from openai import OpenAI
    except ImportError as exc:
        raise OpenAIConfigurationError(
            "OpenAI SDK is not installed. Run: pip install -r requirements.txt"
        ) from exc

    return OpenAI(
        api_key=api_key,
        timeout=get_int_env("OPENAI_TIMEOUT_SECONDS", DEFAULT_TIMEOUT_SECONDS),
        max_retries=get_int_env("OPENAI_MAX_RETRIES", DEFAULT_MAX_RETRIES),
    )


def get_model_name():
    return getenv("OPENAI_MODEL") or DEFAULT_MODEL


def get_reasoning_effort():
    return getenv("OPENAI_REASONING_EFFORT") or DEFAULT_REASONING_EFFORT


def get_max_input_tokens():
    return get_int_env("OPENAI_MAX_INPUT_TOKENS", DEFAULT_MAX_INPUT_TOKENS)


def build_prompt(language):
    static_folder = path.join(getenv("MAIN_FOLDER"), "static")
    base_prompt = open(path.join(static_folder, "cmds/base.txt")).read()
    return base_prompt.replace("@LANGUAGE", language.upper())


def estimate_tokens(text):
    if not text:
        return 0
    char_estimate = ceil(len(text) / TOKEN_CHAR_RATIO)
    word_estimate = ceil(len(text.split()) * TOKEN_WORD_RATIO)
    return max(char_estimate, word_estimate)


def split_transcript_blocks(text):
    return [block.strip() for block in text.split("---") if block.strip()]


def format_transcript_blocks(blocks):
    blocks = list(blocks)
    if not blocks:
        return ""
    return "\n---\n\n".join(blocks) + "\n---\n\n"


def truncate_text_to_tokens(text, max_tokens):
    if estimate_tokens(text) <= max_tokens:
        return text
    if max_tokens <= 0:
        return ""

    trimmed = text[: max(1, max_tokens * TOKEN_CHAR_RATIO)].rstrip()
    while trimmed and estimate_tokens(trimmed) > max_tokens:
        next_length = max(1, int(len(trimmed) * 0.9))
        if next_length >= len(trimmed):
            return ""
        trimmed = trimmed[:next_length].rstrip()
    return trimmed


def trim_old_transcripts(text, max_tokens):
    before_tokens = estimate_tokens(text)
    if before_tokens <= max_tokens:
        return text, {
            "trimmed": False,
            "before_tokens": before_tokens,
            "after_tokens": before_tokens,
            "total_blocks": len(split_transcript_blocks(text)),
            "kept_blocks": len(split_transcript_blocks(text)),
            "dropped_blocks": 0,
        }

    blocks = split_transcript_blocks(text)
    if not blocks:
        trimmed_text = truncate_text_to_tokens(text, max_tokens)
        return trimmed_text, {
            "trimmed": True,
            "before_tokens": before_tokens,
            "after_tokens": estimate_tokens(trimmed_text),
            "total_blocks": 0,
            "kept_blocks": 0,
            "dropped_blocks": 0,
        }

    kept_reversed = []
    for block in reversed(blocks):
        candidate_reversed = kept_reversed + [block]
        candidate_text = format_transcript_blocks(reversed(candidate_reversed))
        if estimate_tokens(candidate_text) <= max_tokens:
            kept_reversed = candidate_reversed
            continue

        if not kept_reversed:
            truncated_block = truncate_text_to_tokens(block, max_tokens)
            if truncated_block:
                kept_reversed = [truncated_block]
        break

    trimmed_text = format_transcript_blocks(reversed(kept_reversed))
    if estimate_tokens(trimmed_text) > max_tokens:
        trimmed_text = truncate_text_to_tokens(trimmed_text, max_tokens)
    kept_blocks = len(kept_reversed)
    return trimmed_text, {
        "trimmed": True,
        "before_tokens": before_tokens,
        "after_tokens": estimate_tokens(trimmed_text),
        "total_blocks": len(blocks),
        "kept_blocks": kept_blocks,
        "dropped_blocks": max(0, len(blocks) - kept_blocks),
    }


def prepare_category_transcript(category, text):
    max_tokens = get_max_input_tokens()
    trimmed_text, stats = trim_old_transcripts(text, max_tokens)
    if stats.get("trimmed"):
        logger.warning(
            f"{category} [OpenAI] > trimmed input from "
            f"{stats.get('before_tokens')} to {stats.get('after_tokens')} "
            f"estimated token(s); kept {stats.get('kept_blocks')}/"
            f"{stats.get('total_blocks')} block(s), dropped "
            f"{stats.get('dropped_blocks')} oldest"
        )
    return trimmed_text


def generate_category_facts(client, model, reasoning_effort, transcript, language):
    response = client.responses.create(
        model=model,
        instructions=build_prompt(language),
        input=transcript,
        reasoning={"effort": reasoning_effort},
        prompt_cache_key=PROMPT_CACHE_KEY,
        text={
            "verbosity": "low",
            "format": {
                "type": "json_schema",
                "name": "flash_facts",
                "schema": FACTS_SCHEMA,
                "strict": True,
            },
        },
    )
    return loads(response.output_text)


def generate_facts(transcripts, language=None, retry=None):
    client = get_openai_client()
    model = get_model_name()
    reasoning_effort = get_reasoning_effort()
    language = language or DEFAULT_LANGUAGE
    facts = dict()

    for category, text in tqdm(transcripts.items(), desc="Generating facts"):
        text = prepare_category_transcript(category, text)
        try:
            json_res = generate_category_facts(
                client, model, reasoning_effort, text, language
            )
        except Exception as e:
            logger.info(f"{model} [OpenAI] ! Error generating '{category}' facts")
            logger.error(f"{model} [OpenAI] > {e}")
            continue

        facts[category] = json_res
        total_facts = len(json_res.get("facts", []))
        logger.info(
            f"{category} > Generated {total_facts} fact(s) with {model} [OpenAI]"
        )

    save_facts(facts)
    return facts


def save_facts(facts):
    json_path = path.join(getenv("MAIN_FOLDER"), "output/output.json")
    with open(json_path, "w+") as file_out:
        dump(facts, file_out, indent=2)
