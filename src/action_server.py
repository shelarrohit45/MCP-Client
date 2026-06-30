"""HTTP server for merge/reject actions linked from PR notification emails."""

from __future__ import annotations

import html
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from action_tokens import ActionTokenError, verify_action_token
from config import Settings
from github_pr import PullRequestActionError, get_pull_request, merge_pull_request, reject_pull_request

ACTION_PATH_RE = re.compile(r"^/pr/(?P<number>\d+)/(?P<action>merge|reject)$")


class ActionServerError(Exception):
    """Raised when the action server cannot start."""


def _page(title: str, body: str, status: int = 200) -> tuple[int, str, bytes]:
    content = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; margin: 2rem; color: #111; }}
    .card {{ max-width: 640px; border: 1px solid #ddd; border-radius: 12px; padding: 1.5rem; }}
    .btn {{ display: inline-block; margin-right: 0.75rem; margin-top: 1rem; padding: 0.7rem 1rem;
            border-radius: 8px; text-decoration: none; color: white; font-weight: 600; }}
    .merge {{ background: #1a7f37; }}
    .reject {{ background: #cf222e; }}
    .muted {{ color: #555; }}
  </style>
</head>
<body>
  <div class="card">
    <h1>{html.escape(title)}</h1>
    {body}
  </div>
</body>
</html>"""
    return status, "text/html; charset=utf-8", content.encode("utf-8")


def _confirmation_page(settings: Settings, pull_number: int, action: str, token: str) -> bytes:
    pr = get_pull_request(settings, pull_number)
    action_label = "Merge" if action == "merge" else "Reject"
    button_class = "merge" if action == "merge" else "reject"
    body = f"""
    <p class="muted">Repository: <strong>{html.escape(settings.github_repo_full)}</strong></p>
    <p><strong>#{pr.number}</strong> {html.escape(pr.title)}</p>
    <p class="muted">Author: {html.escape(pr.author)} · Branch: {html.escape(pr.branch)}</p>
    <p>Confirm you want to <strong>{action_label.lower()}</strong> this pull request.</p>
    <form method="post" action="/pr/{pull_number}/{action}">
      <input type="hidden" name="token" value="{html.escape(token)}">
      <button class="btn {button_class}" type="submit">{action_label} PR</button>
    </form>
    <p class="muted"><a href="{html.escape(pr.url)}">View on GitHub</a></p>
    """
    return _page(f"{action_label} PR #{pull_number}", body)[2]


def _result_page(title: str, message: str, pr_url: str) -> bytes:
    body = f"""
    <p>{html.escape(message)}</p>
    <p class="muted"><a href="{html.escape(pr_url)}">Open pull request on GitHub</a></p>
    """
    return _page(title, body)[2]


def create_action_handler(settings: Settings) -> type[BaseHTTPRequestHandler]:
  class PrActionHandler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args) -> None:  # noqa: A003
      return

    def _send(self, status: int, content_type: str, body: bytes) -> None:
      self.send_response(status)
      self.send_header("Content-Type", content_type)
      self.send_header("Content-Length", str(len(body)))
      self.end_headers()
      self.wfile.write(body)

    def _parse_request(self) -> tuple[int, str, str] | None:
      parsed = urlparse(self.path)
      match = ACTION_PATH_RE.match(parsed.path)
      if not match:
        return None
      pull_number = int(match.group("number"))
      action = match.group("action")
      if self.command == "GET":
        query = parse_qs(parsed.query)
        token = (query.get("token") or [""])[0]
      else:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode("utf-8", errors="replace")
        token = (parse_qs(raw).get("token") or [""])[0]
      return pull_number, action, token

    def _handle(self) -> None:
      parsed = urlparse(self.path)
      if parsed.path == "/health":
        self._send(200, "application/json", b'{"status":"ok"}')
        return

      if parsed.path == "/":
        body = _page(
            "PR Action Server",
            f"""
            <p>Server is running for <strong>{html.escape(settings.github_repo_full)}</strong>.</p>
            <p class="muted">Merge/Reject links from PR notification emails open here.</p>
            <p><a href="/health">Health check</a></p>
            """,
        )[2]
        self._send(200, "text/html; charset=utf-8", body)
        return

      parsed_request = self._parse_request()
      if parsed_request is None:
        body = _page("Not Found", "<p>Unknown action URL.</p>", status=404)[2]
        self._send(404, "text/html; charset=utf-8", body)
        return

      pull_number, action, token = parsed_request
      try:
        verify_action_token(settings.action_secret, token, pull_number, action)
      except ActionTokenError as error:
        body = _page("Invalid Link", f"<p>{html.escape(str(error))}</p>", status=403)[2]
        self._send(403, "text/html; charset=utf-8", body)
        return

      if self.command == "GET":
        body = _confirmation_page(settings, pull_number, action, token)
        self._send(200, "text/html; charset=utf-8", body)
        return

      try:
        pr = get_pull_request(settings, pull_number)
        if action == "merge":
          message = merge_pull_request(settings, pull_number)
          title = f"Merged PR #{pull_number}"
        else:
          message = reject_pull_request(settings, pull_number)
          title = f"Rejected PR #{pull_number}"
        body = _result_page(title, message, pr.url)
        self._send(200, "text/html; charset=utf-8", body)
      except (PullRequestActionError, Exception) as error:  # noqa: BLE001
        body = _page("Action Failed", f"<p>{html.escape(str(error))}</p>", status=500)[2]
        self._send(500, "text/html; charset=utf-8", body)

    def do_GET(self) -> None:
      self._handle()

    def do_POST(self) -> None:
      self._handle()

  return PrActionHandler


def _print_startup_help(settings: Settings, host: str) -> None:
    base = settings.action_base_url
    local_base = "127.0.0.1" in base or "localhost" in base

    print(f"PR action server listening on http://{host}:{settings.action_port}")
    print(f"Email links use: {base}")
    print(f"Test in browser: {base}/health")
    print("Keep this terminal open while using Merge/Reject links.\n")

    if local_base:
        print("NOTE: Links use localhost (127.0.0.1). They work ONLY when:")
        print("  • This server is running (this terminal)")
        print("  • You open the email on THIS Mac (Gmail in browser on Mac)")
        print("\nIf you click from your PHONE, links will fail (site can't be reached).")
        print("For phone support:")
        print("  1. Install ngrok: brew install ngrok")
        print("  2. In a new terminal: ngrok http 8765")
        print("  3. Copy the https://.... URL into .env as ACTION_BASE_URL")
        print("  4. Re-send notification: rm logs/pr_notify_state.json && python src/main.py pr-notify")


def run_action_server(settings: Settings, host: str = "127.0.0.1") -> None:
    handler = create_action_handler(settings)
    try:
        server = ThreadingHTTPServer((host, settings.action_port), handler)
    except OSError as error:
        raise ActionServerError(
            f"Could not start action server on {host}:{settings.action_port}: {error}"
        ) from error

    _print_startup_help(settings, host)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping action server.")
        server.server_close()
