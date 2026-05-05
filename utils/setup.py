from os import getenv, path
from re import search

from googleapiclient.discovery import build
from pymongo import MongoClient
from pymortafix.utils import strict_input
from requests import get

DEFAULT_OPENAI_MODEL = "gpt-5.4-mini"
DEFAULT_OPENAI_REASONING_EFFORT = "low"
DEFAULT_OPENAI_TIMEOUT_SECONDS = "120"
DEFAULT_OPENAI_MAX_RETRIES = "3"
DEFAULT_PROXY_RETRIES = "10"
DEFAULT_PROXY_CLOSE_CONNECTIONS = "true"


def setup(method):
    print("> to SKIP just press ENTER (empty value)")
    if method == "all":
        setup_general()
    if method in ("all", "api"):
        setup_api()
    if method in ("all", "mongo"):
        setup_mongo()
    if method in ("all", "gui"):
        setup_webgui()


def save_value(key, value, is_folder=False):
    if not value:
        return
    main_folder = value if is_folder else getenv("MAIN_FOLDER")
    env_file = path.join(main_folder, ".env")
    content = open(env_file).read() if path.exists(env_file) else ""
    attributes = []
    for row in content.split("\n"):
        if not row or row.startswith("#"):
            continue
        if match := search(r"^\s*(\w+)\s*=\s*\"(.*)\"\s*$", row):
            attributes.append(match.groups())
    new_attributes = dict(attributes) | {key: value}
    with open(env_file, "w+") as file:
        env_text = "\n".join(f'{k}="{v}"' for k, v in new_attributes.items())
        file.write(env_text)


def log_setup(name, value=None, success=True):
    if not success:
        return print(f"[☓] {name} setup gone wrong..")
    if not value:
        return print(f"[↪] {name} setup skipped")
    return print(f"[✓] {name} setup successful")


# GENARAL


def check_path(value):
    if not value:
        return True
    return path.exists(value)


def setup_general():
    default_folder = getenv("MAIN_FOLDER") or path.abspath(".")
    folder_text = f"FlashFact folder [{default_folder}]: "
    main_folder = strict_input(
        folder_text,
        wrong_text=f"Wrong path, retry! {folder_text}",
        check=check_path,
        flush=True,
    )
    save_value("MAIN_FOLDER", path.abspath(main_folder) or default_folder, True)
    log_setup("Main fodler", main_folder)


# API


def mask_apikey(key):
    if not key:
        return ""
    return f"{key[:5]}...{key[-5:]}"


def check_openai_key(key):
    if not key:
        return True
    try:
        from openai import OpenAI

        OpenAI(api_key=key).models.list()
    except Exception:
        return False
    return True


def check_int(value):
    if not value:
        return True
    try:
        int(value)
    except ValueError:
        return False
    return True


def check_bool(value):
    if not value:
        return True
    return value.lower() in ("1", "0", "true", "false", "yes", "no", "y", "n")


def check_yt_key(key):
    if not key:
        return True
    try:
        instance = build("youtube", "v3", developerKey=key).channels()
        instance.list(part="status", id="PewDiePie").execute()
    except Exception:
        return False
    return True


def check_unsplash_key(key):
    if not key:
        return True
    data = get("https://api.unsplash.com/stats/total", params={"client_id": key}).json()
    return "errors" not in data


def setup_api():
    # openai
    openai_key = getenv("OPENAI_API_KEY") or ""
    openai_text = f"OpenAI API key [{mask_apikey(openai_key)}]: "
    openai_apikey = strict_input(
        openai_text,
        wrong_text=f"Wrong key, retry! {openai_text}",
        check=check_openai_key,
        flush=True,
    )
    save_value("OPENAI_API_KEY", openai_apikey)
    log_setup("OpenAI", openai_apikey)

    openai_model = getenv("OPENAI_MODEL") or DEFAULT_OPENAI_MODEL
    model_text = f"OpenAI model [{openai_model}]: "
    model = strict_input(model_text, flush=True)
    save_value("OPENAI_MODEL", model or openai_model)
    log_setup("OpenAI model", model or openai_model)

    reasoning_effort = getenv("OPENAI_REASONING_EFFORT") or DEFAULT_OPENAI_REASONING_EFFORT
    reasoning_text = f"OpenAI reasoning effort [{reasoning_effort}]: "
    reasoning = strict_input(reasoning_text, flush=True)
    save_value("OPENAI_REASONING_EFFORT", reasoning or reasoning_effort)
    log_setup("OpenAI reasoning effort", reasoning or reasoning_effort)

    timeout = getenv("OPENAI_TIMEOUT_SECONDS") or DEFAULT_OPENAI_TIMEOUT_SECONDS
    timeout_text = f"OpenAI timeout seconds [{timeout}]: "
    timeout_value = strict_input(
        timeout_text,
        wrong_text=f"Wrong value, retry! {timeout_text}",
        check=check_int,
        flush=True,
    )
    save_value("OPENAI_TIMEOUT_SECONDS", timeout_value or timeout)
    log_setup("OpenAI timeout", timeout_value or timeout)

    max_retries = getenv("OPENAI_MAX_RETRIES") or DEFAULT_OPENAI_MAX_RETRIES
    retries_text = f"OpenAI max retries [{max_retries}]: "
    retries_value = strict_input(
        retries_text,
        wrong_text=f"Wrong value, retry! {retries_text}",
        check=check_int,
        flush=True,
    )
    save_value("OPENAI_MAX_RETRIES", retries_value or max_retries)
    log_setup("OpenAI retries", retries_value or max_retries)

    # youtube
    yt_key = getenv("YT_API_KEY")
    yt_text = f"YouTube Data API key [{mask_apikey(yt_key)}]: "
    yt_apikey = strict_input(
        yt_text,
        wrong_text=f"Wrong key, retry! {yt_text}",
        check=check_yt_key,
        flush=True,
    )
    save_value("YT_API_KEY", yt_apikey)
    log_setup("YT", yt_apikey)

    proxy_http = getenv("YT_TRANSCRIPT_PROXY_HTTP_URL") or ""
    proxy_http_text = f"YouTube transcript HTTP proxy [{proxy_http}]: "
    proxy_http_value = strict_input(proxy_http_text, flush=True)
    save_value("YT_TRANSCRIPT_PROXY_HTTP_URL", proxy_http_value or proxy_http)
    log_setup("YT transcript HTTP proxy", proxy_http_value)

    proxy_https = getenv("YT_TRANSCRIPT_PROXY_HTTPS_URL") or ""
    proxy_https_text = f"YouTube transcript HTTPS proxy [{proxy_https}]: "
    proxy_https_value = strict_input(proxy_https_text, flush=True)
    save_value("YT_TRANSCRIPT_PROXY_HTTPS_URL", proxy_https_value or proxy_https)
    log_setup("YT transcript HTTPS proxy", proxy_https_value)

    proxy_retries = getenv("YT_TRANSCRIPT_PROXY_RETRIES") or DEFAULT_PROXY_RETRIES
    proxy_retries_text = f"YouTube transcript proxy retries [{proxy_retries}]: "
    proxy_retries_value = strict_input(
        proxy_retries_text,
        wrong_text=f"Wrong value, retry! {proxy_retries_text}",
        check=check_int,
        flush=True,
    )
    save_value("YT_TRANSCRIPT_PROXY_RETRIES", proxy_retries_value or proxy_retries)
    log_setup("YT transcript proxy retries", proxy_retries_value or proxy_retries)

    close_connections = (
        getenv("YT_TRANSCRIPT_PROXY_CLOSE_CONNECTIONS")
        or DEFAULT_PROXY_CLOSE_CONNECTIONS
    )
    close_text = f"YouTube transcript proxy close connections [{close_connections}]: "
    close_value = strict_input(
        close_text,
        wrong_text=f"Wrong value, retry! {close_text}",
        check=check_bool,
        flush=True,
    )
    save_value(
        "YT_TRANSCRIPT_PROXY_CLOSE_CONNECTIONS",
        close_value or close_connections,
    )
    log_setup("YT transcript proxy close connections", close_value or close_connections)

    # unsplash
    unsplash_key = getenv("UNSPLASH_API_KEY")
    unsplash_text = f"Unsplash API key [{mask_apikey(unsplash_key)}]: "
    unsplash_apikey = strict_input(
        unsplash_text,
        wrong_text=f"Wrong key, retry! {unsplash_text}",
        check=check_unsplash_key,
        flush=True,
    )
    save_value("UNSPLASH_API_KEY", unsplash_apikey)
    log_setup("Unsplash", unsplash_apikey)


# MONGO


def setup_mongo():
    if strict_input("Would you like to setup MongoDB? [y/n]: ", flush=True) != "y":
        log_setup("MongoDB")
        return
    mongo_host = strict_input("Mongo host: ", flush=True)
    mongo_username = strict_input("Mongo username: ", flush=True)
    mongo_password = strict_input("Mongo password: ", flush=True)
    mongo_collection = strict_input("Mongo collection name: ", flush=True)
    # try
    connection = (
        f"mongodb+srv://{mongo_username}:{mongo_password}"
        f"@{mongo_host}/?retryWrites=true&w=majority"
        f"&maxIdleTimeMS=30000"
    )
    try:
        MongoClient(connection)
    except Exception:
        log_setup("MongoDB", success=False)
        return
    save_value("MONGO_IP", mongo_host)
    save_value("MONGO_USER", mongo_username)
    save_value("MONGO_PASSWORD", mongo_password)
    save_value("MONGO_COLLECTION", mongo_collection)
    log_setup("MongoDB", "Y")


# WEB GUI


def setup_webgui():
    webgui_host = strict_input("Web GUI host [localhost]: ", flush=True)
    save_value("WEB_GUI_HOST", webgui_host or "0.0.0.0")
    webgui_port = strict_input("Web GUI host [8200]: ", flush=True)
    save_value("WEB_GUI_PORT", webgui_port or 8200)
    log_setup("Web GUI", webgui_host or webgui_port)
