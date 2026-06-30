import sys

from config import ConfigError, load_settings


def main() -> None:
    try:
        settings = load_settings()
    except ConfigError as error:
        print(f"Configuration error: {error}")
        sys.exit(1)

    print("MCP client started")
    print(f"GitHub repo: {settings.github_repo_full}")
    print(f"Email sender: {settings.email_sender}")
    print(f"Recipients: {len(settings.email_recipients)}")
    print("Secrets loaded from .env (not displayed)")


if __name__ == "__main__":
    main()
