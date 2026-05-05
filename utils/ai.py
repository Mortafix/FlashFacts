from json import dump, loads
from os import getenv, path

from dotenv import load_dotenv
from tqdm import tqdm
from utils.logger import logger

load_dotenv()

DEFAULT_MODEL = "gpt-5.4-mini"
DEFAULT_REASONING_EFFORT = "low"
DEFAULT_TIMEOUT_SECONDS = 120
DEFAULT_MAX_RETRIES = 3
DEFAULT_LANGUAGE = "italian"
PROMPT_CACHE_KEY = "flashfacts-facts-v1"

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


class OpenAIConfigurationError(RuntimeError):
    ...


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


def build_prompt(language):
    static_folder = path.join(getenv("MAIN_FOLDER"), "static")
    base_prompt = open(path.join(static_folder, "cmds/base.txt")).read()
    return base_prompt.replace("@LANGUAGE", language.upper())


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
            }
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
        logger.info(f"{category} > Generated {total_facts} fact(s) with {model} [OpenAI]")

    save_facts(facts)
    return facts


def save_facts(facts):
    json_path = path.join(getenv("MAIN_FOLDER"), "output/output.json")
    with open(json_path, "w+") as file_out:
        dump(facts, file_out, indent=2)
