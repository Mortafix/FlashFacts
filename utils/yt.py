from csv import DictReader
from datetime import datetime, timedelta, timezone
from os import getenv, mkdir, path, walk
from shutil import rmtree

from googleapiclient.discovery import build
from joblib import Memory
from tqdm import tqdm
from utils.logger import logger
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import TextFormatter
from youtube_transcript_api.proxies import GenericProxyConfig

memory = Memory(".cache")

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


class TranscriptProxyConfig(GenericProxyConfig):
    def __init__(
        self,
        http_url=None,
        https_url=None,
        close_connections=True,
        retries_when_blocked=10,
    ):
        super().__init__(http_url=http_url, https_url=https_url)
        self._close_connections = close_connections
        self._retries_when_blocked = retries_when_blocked

    @property
    def prevent_keeping_connections_alive(self):
        return self._close_connections

    @property
    def retries_when_blocked(self):
        return self._retries_when_blocked


def get_bool_env(name, default=False):
    value = getenv(name)
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "y", "on")


def get_int_env(name, default):
    value = getenv(name)
    if not value:
        return default
    try:
        return int(value)
    except ValueError:
        logger.warning(f"{name} must be an integer; using {default}")
        return default


def get_transcript_proxy_config():
    http_url = getenv("YT_TRANSCRIPT_PROXY_HTTP_URL") or None
    https_url = getenv("YT_TRANSCRIPT_PROXY_HTTPS_URL") or None
    if not http_url and not https_url:
        return None

    retries = get_int_env("YT_TRANSCRIPT_PROXY_RETRIES", 10)
    close_connections = get_bool_env("YT_TRANSCRIPT_PROXY_CLOSE_CONNECTIONS", True)
    logger.info("YouTube transcripts > proxy enabled")
    return TranscriptProxyConfig(
        http_url=http_url,
        https_url=https_url,
        close_connections=close_connections,
        retries_when_blocked=retries,
    )


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
    trascript_folder = path.join(getenv("MAIN_FOLDER"), "output/transcripts")
    if path.exists(trascript_folder):
        rmtree(trascript_folder)
    mkdir(trascript_folder)
    # trascipts
    formatter = TextFormatter()
    transcript_api = YouTubeTranscriptApi(proxy_config=get_transcript_proxy_config())
    for category, cat_videos in videos.items():
        cat_videos.sort(key=lambda x: x.publish)
        for video in tqdm(cat_videos, desc=f"{category} | Videos"):
            try:
                transcript = transcript_api.fetch(
                    video.id, languages=["it", "en", "es"]
                )
                transcript = formatter.format_transcript(transcript).replace("\n", " ")
                text = f"> {video.title}\n{transcript}\n---\n\n"
                open(path.join(trascript_folder, f"{category}.txt"), "a+").write(text)
            except Exception:
                logger.error(f"{video.channel} ! No transcript found.. ({video.url})")


def get_transcripts(folder):
    transcripts = dict()
    for file in list(walk(folder))[0][2]:
        category, *_ = file.split(".")
        file_path = path.join(folder, file)
        if text := open(file_path).read():
            transcripts[category] = text
    return transcripts
