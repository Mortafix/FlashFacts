from os import getenv, path
from re import search

from google import generativeai
from googleapiclient.discovery import build
from pymongo import MongoClient
from pymortafix.utils import strict_input
from requests import get


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
    attributes = [
        search(r"(\w+)\s*=\s*\"(.+)\"", row).groups()
        for row in content.split("\n")
        if row and not row.startswith("#")
    ]
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


def check_gemini_key(key):
    if not key:
        return True
    try:
        generativeai.configure(api_key=key)
        list(generativeai.list_models())
    except Exception:
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
    # gemini
    gemini_key = getenv("GEMINI_API_KEY") or ""
    gemini_text = f"Gemini API key [{mask_apikey(gemini_key)}]: "
    gemini_apikey = strict_input(
        gemini_text,
        wrong_text=f"Wrong key, retry! {gemini_text}",
        check=check_gemini_key,
        flush=True,
    )
    save_value("GEMINI_API_KEY", gemini_apikey)
    log_setup("Gemini", gemini_apikey)
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
