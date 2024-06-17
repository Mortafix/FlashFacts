from logging import FileHandler, basicConfig, getLevelName, getLogger
from os import getenv, mkdir, path

from dotenv import load_dotenv

load_dotenv()

folder_path = path.join(getenv("MAIN_FOLDER"), "output")
if not path.exists(folder_path):
    mkdir(folder_path)

file_log = path.join(folder_path, "script.log")
basicConfig(format="[%(asctime)s] %(message)s", handlers=[FileHandler(file_log)])
logger = getLogger(__name__)
logger.setLevel(getLevelName("DEBUG"))
