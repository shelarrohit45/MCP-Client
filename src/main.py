import argparse
import sys
import time
import urllib.error
import urllib.request

from action_server import ActionServerError, run_action_server
from agent_chat import AgentChatError, run_ask
from agent_loop import AgentLoopError
from agent_tools import AgentToolError, format_tools_for_cli, list_agent_tools, tool_schemas
from app_logging import get_logger, setup_logging
from config import ConfigError, load_settings
from email_client import EmailSendError, send_test_email
from error_messages import format_error_for_user
from firebase_store import FirebaseStoreError, run_firebase_connectivity_test
from github_fetch import fetch_github_data, print_github_summary, save_github_sample
from llm_client import LLMClientError, chat as llm_chat
from mcp_manager import MCPConnectionError, list_email_tools_sync, list_github_tools_sync
from workflows.ci_alert import CiAlertError, run_ci_alert
from workflows.daily_digest import DailyDigestError, run_daily_digest
from workflows.pr_events import check_pr_events, print_pr_events_summary
from scheduler import SchedulerError, run_scheduler
from workflows.pr_notify import notify_new_pull_requests, print_pr_notify_summary

cli_logger = get_logger("cli")


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


def ci_alert_command(dry_run: bool) -> None:
    settings = load_settings()
    run_ci_alert(settings, dry_run=dry_run)


def digest_command(dry_run: bool, send: bool) -> None:
    settings = load_settings()
    run_daily_digest(settings, dry_run=dry_run, send=send)


def run_scheduler_command() -> None:
    settings = load_settings()
    run_scheduler(settings)


def llm_test_command() -> None:
    settings = load_settings()
    prompt = (
        "You are testing an MCP DevOps client. "
        "Reply with exactly: MCP client LLM test OK"
    )
    print(f"Model: {settings.openrouter_model}")
    print("Sending test prompt to OpenRouter...")
    response = llm_chat(
        settings,
        [{"role": "user", "content": prompt}],
    )
    print(f"Response: {response}")


def firebase_test_command() -> None:
    settings = load_settings()
    print(f"Project: {settings.firebase_project_id}")
    print("Running Firestore connectivity test...")
    result = run_firebase_connectivity_test(settings)
    print("Firebase connection OK.")
    print(f"Session ID: {result['session_id']}")
    print(f"Message ID: {result['message_id']}")
    print(f"Agent run ID: {result['run_id']}")
    print(f"Workflow history ID: {result['history_id']}")
    print(f"Messages read back: {result['message_count']}")
    print("\nCheck Firebase Console → Firestore for these documents.")


def ask_command(question: str, session_id: str | None, dry_run: bool, auto_approve: bool) -> None:
    settings = load_settings()
    result = run_ask(
        settings,
        question,
        session_id=session_id,
        dry_run=dry_run,
        auto_approve=auto_approve,
    )
    print(f"Session: {result.session_id}")
    print(f"Model: {result.model}")
    if dry_run:
        print("Mode: dry-run (preview tools only)")
    if auto_approve:
        print("Mode: auto-approve (sensitive actions run without prompt)")
    if result.prior_message_count:
        print(f"Loaded {result.prior_message_count} prior message(s) from Firebase.")
    if result.tools_called:
        print(f"Tools used: {', '.join(result.tools_called)}")
    print(f"\n{result.response}")
    print(f"\nResume this chat: python src/main.py ask --session {result.session_id} \"...\"")


def agent_tools_command(show_json: bool) -> None:
    if show_json:
        import json

        print(json.dumps(tool_schemas(), indent=2))
        return

    print(format_tools_for_cli())
    print(f"\nTotal: {len(list_agent_tools())} tool(s)")


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

    ci_alert = subparsers.add_parser("ci-alert", help="Send email alert for failed CI runs (last 24h)")
    ci_alert.add_argument("--dry-run", action="store_true", help="Print alert without sending")

    digest = subparsers.add_parser("digest", help="Send daily repository activity digest email")
    digest.add_argument("--dry-run", action="store_true", help="Print digest preview without sending")
    digest.add_argument("--send", action="store_true", help="Send digest email to recipients")

    subparsers.add_parser(
        "run-scheduler",
        help="Run digest and CI alert jobs on schedule (see config/config.yaml)",
    )

    subparsers.add_parser(
        "llm-test",
        help="Test OpenRouter LLM connection (Step 11.1)",
    )

    subparsers.add_parser(
        "firebase-test",
        help="Test Firebase Firestore read/write (Step 11.2)",
    )

    ask = subparsers.add_parser(
        "ask",
        help="Natural language agent chat with tools + Firebase memory (Step 11.3+)",
    )
    ask.add_argument("question", help="Your question in plain English")
    ask.add_argument(
        "--session",
        default=None,
        help="Resume an existing chat session id from a previous ask command",
    )
    ask.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview mode: use preview tools only, no emails sent",
    )
    ask.add_argument(
        "--yes",
        action="store_true",
        help="Skip confirmation prompts for sensitive actions (send email, alerts)",
    )

    agent_tools = subparsers.add_parser(
        "agent-tools",
        help="List agent tools available to the LLM (Step 11.4)",
    )
    agent_tools.add_argument(
        "--json",
        action="store_true",
        help="Print OpenRouter-compatible tool schemas as JSON",
    )
    return parser


def main() -> None:
    setup_logging()
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

        if args.command == "ci-alert":
            ci_alert_command(dry_run=args.dry_run)
            return

        if args.command == "digest":
            if args.dry_run and args.send:
                parser.error("Use only one of --dry-run or --send")
            if not args.dry_run and not args.send:
                parser.error("digest requires --dry-run or --send")
            digest_command(dry_run=args.dry_run, send=args.send)
            return

        if args.command == "run-scheduler":
            run_scheduler_command()
            return

        if args.command == "llm-test":
            llm_test_command()
            return

        if args.command == "firebase-test":
            firebase_test_command()
            return

        if args.command == "ask":
            ask_command(
                question=args.question,
                session_id=args.session,
                dry_run=args.dry_run,
                auto_approve=args.yes,
            )
            return

        if args.command == "agent-tools":
            agent_tools_command(show_json=args.json)
            return

        print_default_summary()
    except ConfigError as error:
        cli_logger.error("configuration_error detail=%s", error)
        print(f"Configuration error: {error}")
        sys.exit(1)
    except MCPConnectionError as error:
        cli_logger.error("mcp_connection_error detail=%s", error)
        print(format_error_for_user(error))
        sys.exit(1)
    except EmailSendError as error:
        cli_logger.error("email_send_error detail=%s", error)
        print(format_error_for_user(error))
        sys.exit(1)
    except CiAlertError as error:
        cli_logger.error("ci_alert_error detail=%s", error)
        print(format_error_for_user(error))
        sys.exit(1)
    except DailyDigestError as error:
        cli_logger.error("daily_digest_error detail=%s", error)
        print(format_error_for_user(error))
        sys.exit(1)
    except ActionServerError as error:
        cli_logger.error("action_server_error detail=%s", error)
        print(format_error_for_user(error))
        sys.exit(1)
    except SchedulerError as error:
        cli_logger.error("scheduler_error detail=%s", error)
        print(format_error_for_user(error))
        sys.exit(1)
    except LLMClientError as error:
        cli_logger.error("llm_client_error detail=%s", error)
        print(format_error_for_user(error))
        sys.exit(1)
    except FirebaseStoreError as error:
        cli_logger.error("firebase_store_error detail=%s", error)
        print(format_error_for_user(error))
        sys.exit(1)
    except AgentChatError as error:
        cli_logger.error("agent_chat_error detail=%s", error)
        print(format_error_for_user(error))
        sys.exit(1)
    except AgentToolError as error:
        cli_logger.error("agent_tool_error detail=%s", error)
        print(format_error_for_user(error))
        sys.exit(1)
    except AgentLoopError as error:
        cli_logger.error("agent_loop_error detail=%s", error)
        print(format_error_for_user(error))
        sys.exit(1)
    except Exception as error:  # noqa: BLE001 - surface MCP failures clearly in CLI
        cli_logger.exception("unhandled_error command=%s", getattr(args, "command", None))
        print(format_error_for_user(error))
        sys.exit(1)


if __name__ == "__main__":
    main()
