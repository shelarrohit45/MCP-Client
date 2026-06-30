import argparse
import sys
import time
import urllib.error
import urllib.request

from action_server import ActionServerError, run_action_server
from config import ConfigError, load_settings
from email_client import EmailSendError, send_test_email
from github_fetch import fetch_github_data, print_github_summary, save_github_sample
from mcp_manager import MCPConnectionError, list_email_tools_sync, list_github_tools_sync
from workflows.pr_events import check_pr_events, print_pr_events_summary
from workflows.pr_notify import notify_new_pull_requests, print_pr_notify_summary


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


def list_email_tools_command() -> None:
    settings = load_settings()
    tools = list_email_tools_sync(settings)
    print(f"Connected to Email MCP ({len(tools)} tools):\n")
    for name in sorted(tools):
        print(f"- {name}")


def send_test_email_command() -> None:
    settings = load_settings()
    message = send_test_email(settings)
    print(message)
    print(f"From: {settings.email_sender}")
    print(f"To: {', '.join(settings.email_recipients)}")


def pr_notify_command(dry_run: bool, resend: bool, pr_number: int | None) -> None:
    settings = load_settings()
    result = notify_new_pull_requests(
        settings,
        dry_run=dry_run,
        resend=resend,
        pr_number=pr_number,
    )
    print_pr_notify_summary(result, resend=resend)


def pr_watch_command(interval_minutes: int, dry_run: bool) -> None:
    settings = load_settings()
    print(f"Watching all PR events every {interval_minutes} minute(s). Press Ctrl+C to stop.")
    print("Events: created, pushed, merged, rejected, reopened, approved, changes_requested, ci_failed, ci_passed, branch_push")
    while True:
        result = check_pr_events(settings, dry_run=dry_run)
        print_pr_events_summary(result)
        time.sleep(interval_minutes * 60)


def action_server_command(host: str) -> None:
    settings = load_settings()
    run_action_server(settings, host=host)


def check_action_server_command() -> None:
    settings = load_settings()
    url = f"{settings.action_base_url}/health"
    try:
        with urllib.request.urlopen(url, timeout=3) as response:
            body = response.read().decode("utf-8", errors="replace")
        print(f"OK: action server reachable at {url}")
        print(body)
    except urllib.error.URLError as error:
        print(f"Action server NOT reachable at {url}")
        print(f"Reason: {error}")
        print("\nFix:")
        print("  1. Start server: python src/main.py action-server")
        print("  2. Test again:  python src/main.py check-action-server")
        print("\nIf email is on your phone, set ACTION_BASE_URL to an ngrok https URL.")
        sys.exit(1)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="MCP DevOps client")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("list-github-tools", help="List GitHub MCP tools")
    subparsers.add_parser("fetch-github", help="Fetch open PRs and failed CI data")
    subparsers.add_parser("list-email-tools", help="List Email MCP tools")
    subparsers.add_parser("send-test-email", help="Send a test email via Email MCP")

    pr_notify = subparsers.add_parser("pr-notify", help="Email notifications for new open PRs")
    pr_notify.add_argument("--dry-run", action="store_true", help="Print emails without sending")
    pr_notify.add_argument(
        "--resend",
        action="store_true",
        help="Send again for open PRs already notified",
    )
    pr_notify.add_argument(
        "--pr",
        type=int,
        default=None,
        help="Only notify this PR number (use with --resend)",
    )

    pr_watch = subparsers.add_parser(
        "pr-watch",
        help="Poll for PR events (created, merged, rejected, approved, …) and email",
    )
    pr_watch.add_argument("--dry-run", action="store_true", help="Print emails without sending")
    pr_watch.add_argument(
        "--interval",
        type=int,
        default=None,
        help="Minutes between checks (default: from config)",
    )

    action_server = subparsers.add_parser(
        "action-server",
        help="Run HTTP server for Merge/Reject links in PR emails",
    )
    action_server.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host to bind (default: 127.0.0.1)",
    )
    subparsers.add_parser("check-action-server", help="Test if PR action server is reachable")

    pr_events = subparsers.add_parser("pr-events", help="Check all PR events once and send emails")
    pr_events.add_argument("--dry-run", action="store_true", help="Print emails without sending")
    pr_events.add_argument("--resend", action="store_true", help="Send again even if already notified")
    pr_events.add_argument("--pr", type=int, default=None, help="Only check this PR number")
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

        if args.command == "list-email-tools":
            list_email_tools_command()
            return

        if args.command == "send-test-email":
            send_test_email_command()
            return

        if args.command == "pr-notify":
            pr_notify_command(dry_run=args.dry_run, resend=args.resend, pr_number=args.pr)
            return

        if args.command == "pr-watch":
            settings = load_settings()
            interval = args.interval or settings.pr_check_interval_minutes
            pr_watch_command(interval_minutes=interval, dry_run=args.dry_run)
            return

        if args.command == "pr-events":
            settings = load_settings()
            result = check_pr_events(
                settings,
                dry_run=args.dry_run,
                resend=args.resend,
                pr_number=args.pr,
            )
            print_pr_events_summary(result)
            return

        if args.command == "action-server":
            action_server_command(host=args.host)
            return

        if args.command == "check-action-server":
            check_action_server_command()
            return

        print_default_summary()
    except ConfigError as error:
        print(f"Configuration error: {error}")
        sys.exit(1)
    except MCPConnectionError as error:
        print(f"MCP connection error: {error}")
        sys.exit(1)
    except EmailSendError as error:
        print(f"Email error: {error}")
        sys.exit(1)
    except ActionServerError as error:
        print(f"Action server error: {error}")
        sys.exit(1)
    except Exception as error:  # noqa: BLE001 - surface MCP failures clearly in CLI
        print(f"Error: {error}")
        sys.exit(1)


if __name__ == "__main__":
    main()
