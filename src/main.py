import argparse
import sys

from config import ConfigError, load_settings
from github_fetch import fetch_github_data, print_github_summary, save_github_sample
from mcp_manager import MCPConnectionError, list_github_tools_sync


def print_default_summary() -> None:
    settings = load_settings()
    print("MCP client started")
    print(f"GitHub repo: {settings.github_repo_full}")
    print(f"Email sender: {settings.email_sender}")
    print(f"Recipients: {len(settings.email_recipients)}")
    print("Secrets loaded from .env (not displayed)")


def list_github_tools_command() -> None:
    settings = load_settings()
    tools = list_github_tools_sync(settings.github_token)
    print(f"Connected to GitHub MCP ({len(tools)} tools):\n")
    for name in sorted(tools):
        print(f"- {name}")


def fetch_github_command() -> None:
    settings = load_settings()
    result = fetch_github_data(settings)
    print_github_summary(result)
    output_path = save_github_sample(result)
    print(f"\nSaved sample data to: {output_path}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="MCP DevOps client")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("list-github-tools", help="List GitHub MCP tools")
    subparsers.add_parser("fetch-github", help="Fetch open PRs and failed CI data")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    try:
        if args.command == "list-github-tools":
            list_github_tools_command()
            return

        if args.command == "fetch-github":
            fetch_github_command()
            return

        print_default_summary()
    except ConfigError as error:
        print(f"Configuration error: {error}")
        sys.exit(1)
    except MCPConnectionError as error:
        print(f"MCP connection error: {error}")
        sys.exit(1)
    except Exception as error:  # noqa: BLE001 - surface MCP failures clearly in CLI
        print(f"Error: {error}")
        sys.exit(1)


if __name__ == "__main__":
    main()
