# Flash Facts

**Flash Facts** is a mini-news website that uses AI to condense news/facts from YT videos.  

Flash Facts provides quick and concise **news summaries** by leveraging artificial intelligence. It gathers news from various sources on YT and delivers them in a condensed format, making it easy to stay updated with minimal effort.

## Features

- **AI-Powered Summarization**: Uses AI models (like ChatGPT and Gemini) to summarize news articles.
- **Diverse News Sources**: Aggregates news from multiple YT channels and/or playlists.
- **User-Friendly Interface**: Simple and modern web GUI.

## Prerequisites

Before the first run, you’ll need the following API keys:

1. [Gemini](https://aistudio.google.com/app/apikey) API key: required for generating news summaries.
2. [YouTube Data API V3](https://developers.google.com/youtube/v3) key: required for fetching videos from YouTube.
3. [Optional] [Unsplash](https://unsplash.com/developers) API key: needed, if you want, to get automatically images from Unsplash.

## Installation & Setup

To get started, follow these steps

```sh
# clone the repo
git clone https://github.com/yourusername/FlashFacts.git
cd FlashFacts

# create a virtual environment
python -m venv venv
source venv/bin/activate # linux and macos
.\venv\Scripts\activate # windows

# install the requirements
pip install -r requirements.txt
```

Create a file named `.env` and fill up the information needed
```env
# file '.env'

MAIN_FOLDER = "/path/to/folder"

GEMINI_API_KEY = <gemini-api-key>
YT_API_KEY = <youtube-api-key>
UNSPLASH_KEY = <unsplash-api-key>
```

## Usage

There are two ways to run the script to fetch and generate news:

1. Provide a **CSV** of [sources](examples/sources.csv)
```bash
python app.py -s examples/sources.csv
```
```env
# example of sources
category    language    type        channel     id
news        en          channel     BBC         @BBCNews
news        it          playlist    Euronews    PLGWKgaTMGTQs65mOM0B_UgwDUzL2BXGcd
...
```
Optional parameters:
- `-d`: Specify the number of days to go back for videos.
```bash
# get last 7 days videos of the sources provided
python app.py -s examples/sources.csv -d 7
```

2. Provide a folder containing [transcripts](examples/transcripts) in **text** format
```bash
python app.py -t examples/transcripts
```

### General optional parameters
- `-l`: Specify the output language.
```sh
python app.py -s examples/sources.csv -l italian
```
- `-o`: Specify the output file path.
```sh
python app.py -s examples/sources.csv -o output_folder/result
```
- `-f`: Specify the output format.
```sh
python app.py -s examples/sources.csv -f json
```
- `--save-on-mongo`: Save the output in a MongoDB collection.
```sh
python app.py -s examples/sources.csv --save-on-mongo
```
To use this last feature you need to add this additional information to `.env` file.
```env
# file '.env'
[...]
MONGO_USER = "mongo-user"
MONGO_PASSWORD = "mongo-password"
MONGO_IP = "mongo-ip"
MONGO_COLLECTION = "collection-name"
```
## Web GUI
In order too Run the web interface, you only need to run the script with `--gui`.  
**WARNING**: Web GUI, for now, onyl works with data on MongoDB 
```bash
python app.py --gui
```
and go to [http://localhost:8200](http://localhost:8200).
> If you want, you can change host and port in the .env file
```env
# file '.env'
[...]
WEB_GUI_HOST = "https://example.host"
WEB_GUI_PORT = 8301
```

## Future Additions
- OpenAI support (ChatGPT API)
- Web GUI news from local folders
