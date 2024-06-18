from argparse import ArgumentParser


def args_parser():
    parser = ArgumentParser(
        prog="flashfacts",
        # description="Do you want to be a pirate? It's FREE.",
        # usage="gold-pirate -q QUERY [-s SORT] [-e ENGINE] [-o OUTPUT]",
        # epilog='Example: gold-pirate -q "Harry Potter" -s size -V',
    )
    parser.add_argument(
        "-s", "--sources", type=str, help="sources file", metavar=("FILE")
    )
    parser.add_argument(
        "-d",
        "--days",
        type=int,
        default=1,
        help="days included for the latest videos",
        metavar=("DAYS"),
    )
    parser.add_argument(
        "-t",
        "--transcripts",
        type=str,
        help="folder containing the text transcriptions",
        metavar=("FOLDER"),
    )
    parser.add_argument(
        "-l",
        "--language",
        type=str,
        default="english",
        help="output language (default: 'english')",
        metavar=("LANGUAGE"),
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        default="output/facts",
        help="output filename (default: 'facts')",
        metavar=("FOLDER"),
    )
    parser.add_argument(
        "-f",
        "--format-output",
        default="text",
        choices=["text", "json", "markdown"],
        help="output format: text, json or markdown (default: %(default)s)",
    )
    parser.add_argument(
        "--save-on-mongo",
        action="store_true",
        help="save facts on MongoDB (mongo access required)",
    )
    parser.add_argument(
        "--gui",
        action="store_true",
        help="web gui for reading the news",
    )
    return parser.parse_args()
