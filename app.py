from datetime import datetime
from json import dump
from locale import LC_TIME, setlocale
from os import getenv, path

from dotenv import load_dotenv
from fastapi import FastAPI, Path, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from utils.ai import generate_facts
from utils.arguments import args_parser
from utils.dates import get_adj_months, get_month_grid, parse_date
from utils.images import search_image
from utils.logger import logger
from utils.mongo import (connect, get_facts_dates, get_facts_from_mongo,
                         save_on_mongo)
from utils.yt import build_transcripts, get_transcripts, get_videos
from uvicorn import run

setlocale(LC_TIME, "it_IT.UTF-8")
load_dotenv()

# ---- Generation with AI


def format_output(facts, fmt):
    if fmt == "json":
        return facts
    if fmt == "markdown":
        return "\n\n".join(
            f"# {category.upper()}\n{data.get('summary')}\n\n"
            + "\n\n".join(
                f"### {fact.get('title')}\n{fact.get('body')}"
                for fact in data.get("facts")
            )
            for category, data in facts.items()
        )
    return "\n\n".join(
        f"{category.upper()}\n\n"
        + "\n\n".join(
            f"{fact.get('title')}\n{fact.get('body')}" for fact in data.get("facts")
        )
        for category, data in facts.items()
    )


def main():
    args = args_parser()
    # checks arguments
    if not args.sources and not args.transcripts:
        return print("ERROR! sources file or transcripts folder must be specified")
    if args.save_on_mongo:
        try:
            connect()
        except Exception:
            return print("ERROR! Check your MongoDB configuration..")

    # get yt videos
    if args.sources:
        try:
            videos = get_videos(args.sources, args.days)
        except Exception as e:
            return logger.error(f"[YouTube API] {e}")
        build_transcripts(videos)

    # get video transcripts
    base_ts_folder = path.join(getenv("MAIN_FOLDER"), "output/transcripts")
    ts_folder = args.transcripts if not args.sources else base_ts_folder
    transcripts = get_transcripts(ts_folder)

    # generate facts with AI
    facts = generate_facts(transcripts)

    # download cover images
    for topic in facts:
        search_image(topic)

    # save on Mongo
    if args.save_on_mongo:
        save_on_mongo(facts)

    # save output
    output = format_output(facts, args.format_output)
    output_exts = {"text": "txt", "markdown": "md", "json": "json"}
    filename = f"{args.output}.{output_exts.get(args.format_output)}"
    with open(filename, "w+") as file_out:
        if args.format_output == "json":
            dump(output, file_out, indent=2)
        if args.format_output in ("text", "markdown"):
            file_out.write(output)


# ---- GUI with FastAPI

app = FastAPI()
app.mount("/assets", StaticFiles(directory="assets"), name="assets")
app.mount("/images", StaticFiles(directory="assets/images"), name="images")
app.mount("/css", StaticFiles(directory="assets/css"), name="css")
app.mount("/js", StaticFiles(directory="assets/js"), name="js")
templates = Jinja2Templates(directory="assets/templates")


def gui():
    run(app, host="0.0.0.0", port=8200)


@app.get("/favicon.ico")
def redirect_favicon():
    return RedirectResponse("/images/logo/icon.png")


@app.get("/", response_class=HTMLResponse)
def home_page(request: Request, date: str = None):
    parsed_date = parse_date(date)
    db_dates = get_facts_dates(parsed_date)
    grid = get_month_grid(parsed_date, db_dates)
    prev_month, next_month = get_adj_months(parsed_date)
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "grid": grid,
            "date": parsed_date,
            "today": datetime.now().day,
            "next_month": next_month,
            "prev_month": prev_month,
        },
    )


@app.get("/{date}", response_class=HTMLResponse)
def index_page(request: Request, date: str = Path(..., pattern=r"\d{2}-\d{2}-\d{4}")):
    facts = get_facts_from_mongo(date) or dict()
    day_str = format(facts.get("day"), "%d %B %Y")
    return templates.TemplateResponse(
        "day.html",
        {
            "request": request,
            "date": date,
            "date_str": day_str,
            "categories": facts.get("output", {}),
        },
    )


@app.get("/{date}/{category}", response_class=HTMLResponse)
def category_page(
    request: Request, category: str, date: str = Path(..., pattern=r"\d{2}-\d{2}-\d{4}")
):
    facts = get_facts_from_mongo(date) or dict()
    cat_facts = facts.get("output", {}).get(category, {}).get("facts", [])
    day_str = format(facts.get("day"), "%d %B %Y")
    return templates.TemplateResponse(
        "category.html",
        {
            "request": request,
            "date": date,
            "date_str": day_str,
            "category": category,
            "facts": cat_facts,
        },
    )


@app.get("/{date}/{category}/{n}", response_class=HTMLResponse)
def fact_page(
    request: Request,
    category: str,
    n: int,
    date: str = Path(..., pattern=r"\d{2}-\d{2}-\d{4}"),
):
    facts = get_facts_from_mongo(date) or dict()
    cat_facts = facts.get("output", {}).get(category, {}).get("facts", [])
    if n <= len(cat_facts):
        fact = cat_facts[n - 1]
    day_str = format(facts.get("day"), "%d %B %Y")
    return templates.TemplateResponse(
        "fact.html",
        {
            "request": request,
            "date": date,
            "date_str": day_str,
            "category": category,
            "fact": fact,
            "n": n,
        },
    )


if __name__ == "__main__":
    gui()
