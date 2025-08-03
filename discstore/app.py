import sys

from discstore.di_container import build_api_app, build_cli_controller

DEFAULT_LIBRARY_PATH = "~/.jukebox/library.json"

def main():
    if len(sys.argv) > 1 and sys.argv[1] == "api":
        import uvicorn

        app = build_api_app(DEFAULT_LIBRARY_PATH)
        uvicorn.run(app, host="0.0.0.0", port=8000)
    else:
        controller = build_cli_controller(DEFAULT_LIBRARY_PATH)
        controller.run()


if __name__ == "__main__":
    main()
