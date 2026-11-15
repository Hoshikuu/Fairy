import argparse

from aiohttp import web
from fairy.web.server import create_app


def main():
    parser = argparse.ArgumentParser(description="Serve Fairy's local web interface.")
    parser.add_argument("--port", type=int, default=8081)
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("Ports must be between 1 and 65535")
    app = create_app()

    web.run_app(app, host="127.0.0.1", port=args.port)


if __name__ == "__main__":
    main()
