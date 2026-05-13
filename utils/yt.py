from csv import DictReader
from datetime import datetime, timedelta, timezone
from html import unescape
from os import getenv, makedirs, path, walk
from re import compile
from shutil import rmtree, which
from time import sleep

from googleapiclient.discovery import build
from joblib import Memory
from tqdm import tqdm
from utils.logger import logger
from yt_dlp import YoutubeDL
from yt_dlp.networking.common import Request
from yt_dlp.networking.impersonate import ImpersonateTarget

memory = Memory(".cache")
logged_cookiefiles = set()
cached_js_runtimes = None

SUBTITLE_FORMATS = ("vtt", "srt", "ttml", "srv3", "srv2", "srv1")
JS_RUNTIME_COMMANDS = (
    ("deno", "deno"),
    ("node", "node"),
    ("node", "nodejs"),
    ("quickjs", "qjs"),
    ("bun", "bun"),
)
DEFAULT_YT_DLP_SLEEP_REQUESTS = 0.75
DEFAULT_YT_DLP_SLEEP_SUBTITLES = 5.0
DEFAULT_YT_DLP_COOKIES_FILE = "static/cookies.txt"
TIMESTAMP_RE = compile(
    r"^\d{1,2}:\d{2}:\d{2}[.,]\d{3}\s+-->\s+"
    r"\d{1,2}:\d{2}:\d{2}[.,]\d{3}"
)
INLINE_TIMESTAMP_RE = compile(r"<\d{1,2}:\d{2}:\d{2}\.\d{3}>")
HTML_TAG_RE = compile(r"<[^>]+>")

# ---- model


class Media:
    def __repr__(self):
        return f"[{self.publish:%Y.%m.%d}] {self.title} ({self.url})"


class YTChannelVideo(Media):
    def __init__(self, data, language):
        snippet = data.get("snippet") or dict()
        self.title = snippet.get("title")
        self.channel = snippet.get("channelTitle")
        self.id = data.get("id", {}).get("videoId")
        self.url = f"https://youtu.be/{self.id}"
        self.publish = datetime.fromisoformat(snippet.get("publishTime"))
        self.thumbnail = snippet.get("thumbnails", {}).get("default", {}).get("url")
        self.language = language


class YTPlaylistVideo(Media):
    def __init__(self, data, language):
        snippet = data.get("snippet") or dict()
        self.title = snippet.get("title")
        self.channel = snippet.get("channelTitle")
        self.id = snippet.get("resourceId", {}).get("videoId")
        self.url = f"https://youtu.be/{self.id}"
        self.publish = datetime.fromisoformat(snippet.get("publishedAt"))
        self.thumbnail = snippet.get("thumbnails", {}).get("default", {}).get("url")
        self.language = language


class YTVideo(Media):
    def __init__(self, yt_video_id, language):
        self.title = "..."
        self.channel = "..."
        self.id = yt_video_id
        self.url = f"https://youtu.be/{self.id}"
        self.publish = datetime.now(timezone.utc)
        self.thumbnail = None
        self.language = language


# ---- utils


class YTDLPLogger:
    def debug(self, msg):
        return None

    def info(self, msg):
        return None

    def warning(self, msg):
        logger.warning(f"yt-dlp > {msg}")

    def error(self, msg):
        logger.error(f"yt-dlp > {msg}")


def get_main_folder():
    return getenv("MAIN_FOLDER") or path.abspath(".")


def get_ydl_opts(**opts):
    base_opts = {
        "quiet": True,
        "no_warnings": True,
        "js_runtimes": get_js_runtimes(),
        "sleep_interval_requests": get_float_env(
            "YT_DLP_SLEEP_REQUESTS", DEFAULT_YT_DLP_SLEEP_REQUESTS
        ),
        "sleep_interval_subtitles": get_float_env(
            "YT_DLP_SLEEP_SUBTITLES", DEFAULT_YT_DLP_SLEEP_SUBTITLES
        ),
        "logger": YTDLPLogger(),
    }
    if cookiefile := get_cookiefile():
        base_opts["cookiefile"] = cookiefile
    return base_opts | opts


def get_float_env(name, default):
    value = getenv(name)
    if not value:
        return default
    try:
        return float(value)
    except ValueError:
        logger.warning(f"{name} must be a number; using {default}")
        return default


def get_cookiefile():
    cookiefile = getenv("YT_DLP_COOKIES_FILE") or get_default_cookiefile()
    if not cookiefile:
        return None
    cookiefile = resolve_project_path(cookiefile)
    if not path.exists(cookiefile):
        logger.warning(f"YT_DLP_COOKIES_FILE does not exist: {cookiefile}")
        return None
    log_cookiefile(cookiefile)
    return cookiefile


def log_cookiefile(cookiefile):
    if cookiefile in logged_cookiefiles:
        return
    size = path.getsize(cookiefile)
    if size <= 0:
        logger.warning(f"YT_DLP_COOKIES_FILE is empty: {cookiefile}")
        return
    logger.info(f"yt-dlp > using cookies file ({size} bytes): {cookiefile}")
    logged_cookiefiles.add(cookiefile)


def get_default_cookiefile():
    cookiefile = resolve_project_path(DEFAULT_YT_DLP_COOKIES_FILE)
    return cookiefile if path.exists(cookiefile) else None


def resolve_project_path(file_path):
    file_path = path.expanduser(file_path)
    if path.isabs(file_path):
        return file_path
    return path.join(get_main_folder(), file_path)


def get_js_runtimes():
    global cached_js_runtimes
    if cached_js_runtimes is not None:
        return cached_js_runtimes

    if js_runtime := get_explicit_js_runtime():
        cached_js_runtimes = js_runtime
        return js_runtime
    for runtime, command in JS_RUNTIME_COMMANDS:
        if runtime_path := which(command):
            cached_js_runtimes = {runtime: {"path": runtime_path}}
            return cached_js_runtimes
    logger.warning(
        "yt-dlp > no JavaScript runtime found; install deno, node, quickjs or bun"
    )
    cached_js_runtimes = {"deno": {}}
    return cached_js_runtimes


def get_explicit_js_runtime():
    runtime = getenv("YT_DLP_JS_RUNTIME") or "node"
    runtime_path = getenv("YT_DLP_JS_RUNTIME_PATH")
    if not runtime_path:
        return None

    runtime_path = path.expanduser(runtime_path)
    if not path.exists(runtime_path):
        logger.warning(f"YT_DLP_JS_RUNTIME_PATH does not exist: {runtime_path}")
        return None

    return {runtime: {"path": runtime_path}}


def get_subtitle_language(captions, language, prefer_original=False):
    if not captions:
        return None
    if prefer_original:
        candidates = [f"{language}-orig", language]
    else:
        candidates = [language, f"{language}-orig"]
    candidates += sorted(
        lang for lang in captions if lang.startswith(f"{language}-")
    )
    for candidate in candidates:
        if candidate in captions:
            return candidate
    return None


def get_subtitle_format(subtitles):
    for subtitle_format in SUBTITLE_FORMATS:
        for subtitle in subtitles:
            if subtitle.get("ext") == subtitle_format:
                return subtitle
    return None


def get_yt_dlp_subtitle(info, language):
    manual_language = get_subtitle_language(info.get("subtitles"), language)
    if manual_language:
        return get_subtitle_format(info.get("subtitles", {}).get(manual_language, []))

    automatic_language = get_subtitle_language(
        info.get("automatic_captions"), language, prefer_original=True
    )
    if automatic_language:
        return get_subtitle_format(
            info.get("automatic_captions", {}).get(automatic_language, [])
        )

    return None


def download_subtitle(ydl, subtitle):
    subtitle_sleep = get_float_env(
        "YT_DLP_SLEEP_SUBTITLES", DEFAULT_YT_DLP_SLEEP_SUBTITLES
    )
    if subtitle_sleep:
        sleep(subtitle_sleep)

    extensions = {}
    if impersonate := get_impersonate_target(subtitle.get("impersonate")):
        extensions["impersonate"] = impersonate

    response = ydl.urlopen(
        Request(
            subtitle.get("url"),
            headers=subtitle.get("http_headers") or {},
            extensions=extensions,
        )
    )
    return response.read().decode("utf-8", errors="ignore")


def get_impersonate_target(value):
    if isinstance(value, ImpersonateTarget):
        return value
    if value is True:
        return ImpersonateTarget()
    if isinstance(value, str):
        return ImpersonateTarget.from_str(value)
    return None


def normalize_subtitle_text(content):
    lines = []
    previous = None
    for raw_line in content.splitlines():
        line = raw_line.strip().replace("\ufeff", "")
        if not line or line in ("WEBVTT", "Kind: captions"):
            continue
        if line.startswith(("NOTE", "Language:")):
            continue
        if line.isdigit() or TIMESTAMP_RE.match(line):
            continue

        line = INLINE_TIMESTAMP_RE.sub("", line)
        line = HTML_TAG_RE.sub("", line)
        line = unescape(line).strip()
        if not line or line == previous:
            continue

        lines.append(line)
        previous = line

    return " ".join(lines)


def download_transcript(video):
    with YoutubeDL(get_ydl_opts(skip_download=True)) as ydl:
        info = ydl.extract_info(video.url, download=False)
        subtitle = get_yt_dlp_subtitle(info, video.language)
        if not subtitle:
            raise ValueError(f"no subtitles found for language '{video.language}'")

        transcript = normalize_subtitle_text(download_subtitle(ydl, subtitle))

    if not transcript:
        raise ValueError("empty subtitle text")

    return transcript


def get_cached_transcript(video, cache_folder):
    cache_file = path.join(cache_folder, f"{video.id}.txt")
    if path.exists(cache_file):
        logger.info(f"{video.channel} @ transcript cache hit ({video.url})")
        return open(cache_file, encoding="utf-8").read()

    transcript = download_transcript(video)
    with open(cache_file, "w+", encoding="utf-8") as file:
        file.write(transcript)
    return transcript


@memory.cache(verbose=0)
def get_channel_id(handle):
    youtube = build("youtube", "v3", developerKey=getenv("YT_API_KEY")).search()
    request = youtube.list(part="snippet", q=handle, type="channel")
    response = request.execute()
    if not (item := response.get("items")):
        return None
    return item[0].get("snippet", {}).get("channelId")


def get_latest_channel_videos(channel_id, language):
    youtube = build("youtube", "v3", developerKey=getenv("YT_API_KEY")).search()
    request = youtube.list(
        part="snippet",
        channelId=channel_id,
        maxResults=50,
        order="date",
        type="video",
    )
    return [YTChannelVideo(vid, language) for vid in request.execute().get("items", [])]


def get_latest_playlist_videos(playlist_id, language):
    youtube = build("youtube", "v3", developerKey=getenv("YT_API_KEY")).playlistItems()
    request = youtube.list(
        part="snippet",
        playlistId=playlist_id,
        maxResults=50,
    )
    return [YTPlaylistVideo(vd, language) for vd in request.execute().get("items", [])]


# ---- app


def get_videos(sources_file, last_days=7):
    videos = dict()
    data = [source for source in DictReader(open(sources_file))]
    for source in tqdm(data, desc="Sources"):
        lang, media_id = source.get("language"), source.get("id")
        last_videos = []
        if source.get("type") == "channel":
            channel_id = get_channel_id(media_id) if media_id[0] == "@" else media_id
            last_videos = get_latest_channel_videos(channel_id, lang)
        if source.get("type") == "playlist":
            last_videos = get_latest_playlist_videos(media_id, lang)
        if source.get("type") == "video":
            last_videos = [YTVideo(media_id, lang)]
        last_days_videos = [
            video
            for video in last_videos
            if video.publish > datetime.now(timezone.utc) - timedelta(days=last_days)
        ]
        # save
        category, title = source.get("category"), source.get("channel")
        logger.info(f"{title} > Found {len(last_days_videos)} video(s)")
        for video in last_days_videos:
            logger.info(f"{title} @ {video.title[:50]} ({video.url})")
        videos[category] = videos.get(category, []) + last_days_videos
    return videos


def build_transcripts(videos):
    # folders
    transcript_folder = path.join(get_main_folder(), "output/transcripts")
    cache_folder = path.join(get_main_folder(), "output/transcript_cache")
    if path.exists(transcript_folder):
        rmtree(transcript_folder)
    makedirs(transcript_folder)
    makedirs(cache_folder, exist_ok=True)
    # transcripts
    for category, cat_videos in videos.items():
        cat_videos.sort(key=lambda x: x.publish)
        for video in tqdm(cat_videos, desc=f"{category} | Videos"):
            try:
                transcript = get_cached_transcript(video, cache_folder)
                text = f"> {video.title}\n{transcript}\n---\n\n"
                open(path.join(transcript_folder, f"{category}.txt"), "a+").write(text)
            except Exception as e:
                logger.error(
                    f"{video.channel} ! No transcript found.. ({video.url}) [{e}]"
                )


def get_transcripts(folder):
    transcripts = dict()
    for file in list(walk(folder))[0][2]:
        category, *_ = file.split(".")
        file_path = path.join(folder, file)
        if text := open(file_path).read():
            transcripts[category] = text
    return transcripts
