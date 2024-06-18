from os import getenv, path

import requests
from utils.logger import logger

BASE_URL = "https://api.unsplash.com/search/photos"


def image_exists(query):
    query = query.replace(" ", "_")
    image_path = path.join(getenv("MAIN_FOLDER"), f"assets/images/{query}.jpg")
    return path.exists(image_path)


def search_image(query):
    if not (api_key := getenv("UNSPLASH_KEY")):
        return
    if image_exists(query):
        return
    params = {
        "query": query,
        "client_id": api_key,
        "per_page": 1,
        "orientation": "portrait",
    }
    data = requests.get(BASE_URL, params=params).json()
    regular_image = data["results"][0]["urls"]["regular"]
    return download_image(query, regular_image)


def download_image(query, image_url):
    query = query.replace(" ", "_")
    image_folder = path.join(getenv("MAIN_FOLDER"), "assets/images")
    image_content = requests.get(image_url).content
    open(path.join(image_folder, f"{query}.jpg"), "wb+").write(image_content)
    logger.info(f"{query} > download cover image")
