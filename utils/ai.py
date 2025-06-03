from csv import DictReader
from datetime import datetime, timedelta
from json import dump, loads
from os import getenv, path
from re import search
from time import sleep

from dotenv import load_dotenv
from google import generativeai
from tqdm import tqdm
from utils.logger import logger

load_dotenv()

generativeai.configure(api_key=getenv("GEMINI_API_KEY"))

# ---- utils


class TokenLimitError(Exception):
    ...


class Model:
    def __init__(self, brand, model, rpm, tpm):
        self.brand = brand
        self.name = model
        self.rpm = int(rpm)
        self.tpm = int(tpm)
        self.last_time_used = datetime.min
        self.last_token_used = 0

    def __repr__(self):
        return f"{self.name} [{self.brand}]"

    def can_be_used(self, tokens, prompt):
        # token > max
        if tokens > self.tpm:
            return False
        # delay token
        next_min_req = self.last_time_used + timedelta(minutes=1)
        token_last_minute = self.last_token_used if next_min_req > datetime.now() else 0
        token_missing = self.tpm - token_last_minute
        next_req_token = next_min_req if token_missing > 0 else datetime.min
        # delay requests
        delay_s = (60 / self.rpm) - (datetime.now() - self.last_time_used).seconds
        next_tok_req = datetime.now() + timedelta(seconds=delay_s)
        next_req_time = next_tok_req if delay_s > 0 else datetime.min
        return max(next_req_token, next_req_time)


class Gemini(Model):
    def __init__(self, model, rpm, tpm, input_price, output_price):
        super().__init__("Google", model, rpm, tpm)
        self.model = generativeai.GenerativeModel(model)

    def generate(self, prompt):
        tokens = self.model.count_tokens(prompt).total_tokens
        if not (next_req := self.can_be_used(tokens, prompt)):
            raise TokenLimitError(
                f"Prompt tokens ({tokens}) exceed the limit ({self.tpm})"
            )
        now = datetime.now()
        if next_req and now < next_req:
            delay_s = (next_req - now).seconds + 2
            logger.debug(f"{self} | waiting {delay_s} second(s)")
            sleep(delay_s)
        # generate
        response = self.model.generate_content(prompt)
        self.last_time_used = datetime.now()
        self.last_token_used = tokens
        return response


def parse_json_response(response):
    response_regex = r"```(?:json)?((?:\s|.)+?)```"
    return loads(search(response_regex, response.text).group(1).strip())


# ---- generation


def generate_facts(transcripts, language, retry=True):
    # promtps
    static_folder = path.join(getenv("MAIN_FOLDER"), "static")
    base_prompt = open(path.join(static_folder, "cmds/base.txt")).read()
    base_prompt = base_prompt.replace("@LANGUAGE", language.upper())
    retry_prompt = open(path.join(static_folder, "cmds/retry.txt")).read()
    # models
    models = {"google": Gemini}
    available_models = [
        models.get(row.pop("brand"))(**row)
        for row in DictReader(open(path.join(static_folder, "ai_models.csv")))
    ]
    # generation
    facts = dict()
    # categories
    for category, text in tqdm(transcripts.items(), desc="Generating facts"):
        for model in available_models:
            # response
            try:
                response = model.generate(base_prompt + text)
            except TokenLimitError:
                continue
            except Exception as e:
                logger.info(f"{model} ! Error generating '{category}' facts")
                logger.error(f"{model} > {e}")
                continue
            try:
                json_res = None
                json_res = parse_json_response(response)
            except Exception:
                # rebuild json response
                try:
                    base_model = available_models[-1]
                    source = json_res or response.text
                    response = base_model.generate(retry_prompt + source)
                    json_res = parse_json_response(response)
                except Exception as e:
                    logger.info(f"{model} ! Error rebuilding '{category}' JSON")
                    logger.error(f"{model} > {e}")
                    continue
            # save response
            facts[category] = json_res
            total_facts = len(json_res.get("facts"))
            logger.info(f"{category} > Generated {total_facts} fact(s) with {model}")
            break
    save_facts(facts)
    return facts


def save_facts(facts):
    json_path = path.join(getenv("MAIN_FOLDER"), "output/output.json")
    dump(facts, open(json_path, "w+"), indent=2)
