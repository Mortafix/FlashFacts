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
DEFAULT_YT_DLP_SLEEP_REQUESTS = "0.75"
DEFAULT_YT_DLP_SLEEP_SUBTITLES = "5"
DEFAULT_YT_DLP_COOKIES_FILE = "static/cookies.txt"


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


def check_cookie_path(value):
    if not value:
        return True
    return path.exists(resolve_project_path(value))


def get_default_cookiefile():
    cookiefile = resolve_project_path(DEFAULT_YT_DLP_COOKIES_FILE)
    return cookiefile if path.exists(cookiefile) else ""


def resolve_project_path(file_path):
    file_path = path.expanduser(file_path)
    if path.isabs(file_path):
        return file_path
    return path.join(getenv("MAIN_FOLDER") or path.abspath("."), file_path)


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


def check_float(value):
    if not value:
        return True
    try:
        float(value)
    except ValueError:
        return False
    return True


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

    cookies_file = getenv("YT_DLP_COOKIES_FILE") or get_default_cookiefile()
    cookies_text = f"yt-dlp YouTube cookies file [{cookies_file}]: "
    cookies_value = strict_input(
        cookies_text,
        wrong_text=f"Wrong path, retry! {cookies_text}",
        check=check_cookie_path,
        flush=True,
    )
    save_value("YT_DLP_COOKIES_FILE", cookies_value or cookies_file)
    log_setup("yt-dlp cookies file", cookies_value or cookies_file)

    sleep_requests = getenv("YT_DLP_SLEEP_REQUESTS") or DEFAULT_YT_DLP_SLEEP_REQUESTS
    sleep_requests_text = f"yt-dlp sleep between requests [{sleep_requests}]: "
    sleep_requests_value = strict_input(
        sleep_requests_text,
        wrong_text=f"Wrong value, retry! {sleep_requests_text}",
        check=check_float,
        flush=True,
    )
    save_value("YT_DLP_SLEEP_REQUESTS", sleep_requests_value or sleep_requests)
    log_setup("yt-dlp request sleep", sleep_requests_value or sleep_requests)

    sleep_subtitles = getenv("YT_DLP_SLEEP_SUBTITLES") or DEFAULT_YT_DLP_SLEEP_SUBTITLES
    sleep_subtitles_text = f"yt-dlp sleep before subtitles [{sleep_subtitles}]: "
    sleep_subtitles_value = strict_input(
        sleep_subtitles_text,
        wrong_text=f"Wrong value, retry! {sleep_subtitles_text}",
        check=check_float,
        flush=True,
    )
    save_value("YT_DLP_SLEEP_SUBTITLES", sleep_subtitles_value or sleep_subtitles)
    log_setup("yt-dlp subtitle sleep", sleep_subtitles_value or sleep_subtitles)

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
