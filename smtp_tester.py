#!/usr/bin/env python3
"""SMTP Server Tester"""

import smtplib
import ssl
import sys
import re
import getpass
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path


# ── ANSI ───────────────────────────────────────────────────────────────────────

R   = "\033[0m"
DIM = "\033[2m"
B   = "\033[1m"
G   = "\033[38;5;78m"    # mint green
E   = "\033[38;5;203m"   # soft red
W   = "\033[38;5;221m"   # amber
C   = "\033[38;5;153m"   # steel blue (accents)

def g(t, *c): return "".join(c) + t + R
def dim(t):   return g(t, DIM)
def ok(t):    return g(t, G)
def err(t):   return g(t, E)
def hi(t):    return g(t, B)
def ac(t):    return g(t, C)


# ── Layout ─────────────────────────────────────────────────────────────────────

COL = 10   # label column width

def stage(n, total, title):
    print(f"\n{dim('·' * 54)}")
    print(f"  {dim(f'{n}/{total}')}  {hi(title)}\n")

def field(label, value=""):
    pad = " " * (COL - len(label))
    return f"  {dim(label)}{pad}{value}"

def ask(label, default=None, secret=False, hint=None):
    pad  = " " * (COL - len(label))
    dflt = f"  {dim('default: ' + str(default))}" if default else ""
    h    = f"\n  {dim(hint)}" if hint else ""
    if h: print(h)
    disp = f"  {dim(label)}{pad}{dim('['+ str(default) +'] ') if default else ''}"
    val  = getpass.getpass(disp) if secret else input(disp).strip()
    return val if val else (default or "")

def ask_int(label, default):
    while True:
        try: return int(ask(label, default=str(default)))
        except ValueError: print(err("  not a number"))

def info(text):  print(f"  {dim('·')} {text}")
def good(text):  print(f"  {ok('✓')} {text}")
def bad(text):   print(f"  {err('✗')} {text}")
def warn(text):  print(f"  {g('!', W)} {text}")


# ── File helpers ───────────────────────────────────────────────────────────────

def load_file_recipients(path: str) -> list[str]:
    p = Path(path.strip())
    if not p.exists():
        bad(f"file not found: {path}"); return []
    parts = re.split(r"[,;\n]+", p.read_text(encoding="utf-8"))
    return [x.strip() for x in parts if x.strip()]

def load_file_body(path: str) -> tuple[str, str | None]:
    p = Path(path.strip())
    if not p.exists():
        bad(f"file not found: {path}"); return "", None
    content = p.read_text(encoding="utf-8")
    if p.suffix.lower() == ".md":
        try:
            import markdown
            return content, markdown.markdown(content)
        except ImportError:
            warn("pip install markdown  for HTML rendering — using plain text")
    return content, None


# ── SMTP connection ────────────────────────────────────────────────────────────

def make_connection(cfg: dict) -> smtplib.SMTP:
    host, port = cfg["host"], cfg["port"]
    print(field("status", dim(f"connecting to {host}:{port} …")), end="\r", flush=True)
    try:
        if cfg["ssl"]:
            srv = smtplib.SMTP_SSL(host, port, context=ssl.create_default_context(), timeout=10)
        else:
            srv = smtplib.SMTP(host, port, timeout=10)
            if cfg["tls"]:
                srv.ehlo(); srv.starttls(context=ssl.create_default_context()); srv.ehlo()
        if cfg["user"] and cfg["pass"]:
            srv.login(cfg["user"], cfg["pass"])
        print(field("status", ok("connected ✓") + "        "))
        return srv
    except smtplib.SMTPAuthenticationError:
        print(field("status", err("auth failed ✗") + "        "))
        bad("wrong username or password"); sys.exit(1)
    except (smtplib.SMTPException, OSError) as e:
        print(field("status", err("failed ✗") + "        "))
        bad(str(e)); sys.exit(1)


def ensure_connected(srv: smtplib.SMTP, cfg: dict) -> smtplib.SMTP:
    """Ping the server; silently reconnect if the connection dropped."""
    try:
        srv.noop()
        return srv
    except Exception:
        warn("connection lost — reconnecting …")
        return make_connection(cfg)


# ── Stage 1 ────────────────────────────────────────────────────────────────────

def stage_connect() -> tuple[smtplib.SMTP, dict]:
    stage(1, 2, "CONNECT")

    host = ask("host")
    port = ask_int("port", 587)
    user = ask("user", default="")
    pw   = ask("pass", secret=True) if user else ""

    if   port == 465: ssl_, tls = True,  False;  info("SSL/TLS mode")
    elif port == 587: ssl_, tls = False, True;   info("STARTTLS mode")
    else:
        mode = ask("mode", default="starttls", hint="starttls · ssl · plain")
        ssl_ = mode.lower() == "ssl"
        tls  = mode.lower() == "starttls"

    cfg = dict(host=host, port=port, user=user, **{"pass": pw}, ssl=ssl_, tls=tls)
    srv = make_connection(cfg)
    return srv, cfg


# ── Stage 2 ────────────────────────────────────────────────────────────────────

def read_body_interactive(prev_plain: str | None) -> tuple[str, None]:
    """
    Multiline body input. Ctrl+D (EOF) to finish.
    Returns (plain_text, None).
    """
    pad = " " * COL
    if prev_plain:
        print(f"  {dim('body')}{' ' * (COL - 4)}{dim('Ctrl+D to finish · Enter to reuse previous')}")
    else:
        print(f"  {dim('body')}{' ' * (COL - 4)}{dim('Ctrl+D to finish')}")
    lines = []
    while True:
        try:
            line = input(f"  {pad}")
            lines.append(line)
        except EOFError:
            # Ctrl+D
            print()  # newline after ^D
            break
    text = "\n".join(lines).strip()
    if not text and prev_plain:
        info("reusing previous body")
        return prev_plain, None
    return text, None


def compose(prev: dict | None = None) -> dict:
    p = prev or {}
    stage(2, 2, "COMPOSE")

    from_name  = ask("from",    default=p.get("from_name", ""))
    from_email = ask("address", default=p.get("from_email", ""))

    # Recipients
    prev_to = ", ".join(p.get("recipients", [])) if p.get("recipients") else None
    raw_to  = ask("to", default=prev_to,
                  hint="comma-separated addresses   @file.txt  to import a list")

    if raw_to.startswith("@"):
        path = raw_to[1:].strip()
        recipients = load_file_recipients(path)
        if not recipients: sys.exit(1)
        info(f"loaded {len(recipients)} recipient{'s' if len(recipients)>1 else ''} from {path}")
    else:
        recipients = [x.strip() for x in re.split(r"[,;]+", raw_to) if x.strip()]

    if not recipients:
        bad("no valid recipients"); sys.exit(1)

    subject = ask("subject", default=p.get("subject", ""))

    # Body
    prev_body = p.get("body_plain")
    body_hint = ask("body", default=None,
                    hint="@file.txt · @email.md  to load from file   or press Enter to type")
    if body_hint.startswith("@"):
        path = body_hint[1:].strip()
        body_plain, body_html = load_file_body(path)
        if not body_plain: sys.exit(1)
        info(f"loaded body from {path}")
    elif body_hint:
        # first line already typed — keep collecting until Ctrl+D
        pad = " " * COL
        print(f"  {dim('...')}{' ' * (COL - 3)}{dim('Ctrl+D to finish')}")
        lines = [body_hint]
        while True:
            try:
                line = input(f"  {pad}")
                lines.append(line)
            except EOFError:
                print(); break
        body_plain = "\n".join(lines).strip()
        body_html  = None
    else:
        # user pressed Enter with no input → interactive multiline
        body_plain, body_html = read_body_interactive(prev_body)

    return dict(
        from_name=from_name, from_email=from_email,
        recipients=recipients, subject=subject,
        body_plain=body_plain, body_html=body_html,
    )


# ── Send ───────────────────────────────────────────────────────────────────────

_CONN_ERRORS = (
    smtplib.SMTPServerDisconnected,
    smtplib.SMTPConnectError,
    smtplib.SMTPHeloError,
    ConnectionResetError,
    BrokenPipeError,
    OSError,
)

def do_send(srv: smtplib.SMTP, cfg: dict, draft: dict) -> tuple[smtplib.SMTP, int]:
    """
    Send to all recipients. Reconnects once on connection error.
    Returns (server, sent_count).
    """
    srv = ensure_connected(srv, cfg)
    print()

    sent = 0
    for addr in draft["recipients"]:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = draft["subject"]
        msg["From"]    = (f"{draft['from_name']} <{draft['from_email']}>"
                          if draft["from_name"] else draft["from_email"])
        msg["To"]      = addr
        msg.attach(MIMEText(draft["body_plain"], "plain", "utf-8"))
        if draft.get("body_html"):
            msg.attach(MIMEText(draft["body_html"], "html", "utf-8"))

        try:
            srv.sendmail(draft["from_email"], [addr], msg.as_string())
            good(addr)
            sent += 1
        except _CONN_ERRORS:
            warn(f"connection error while sending to {addr} — reconnecting …")
            srv = make_connection(cfg)
            try:
                srv.sendmail(draft["from_email"], [addr], msg.as_string())
                good(addr)
                sent += 1
            except Exception as e2:
                bad(f"{addr}  ({e2})")
        except smtplib.SMTPException as e:
            bad(f"{addr}  ({e})")

    return srv, sent


# ── Post-send menu ─────────────────────────────────────────────────────────────

def post_send_menu() -> str:
    print(f"\n{dim('·' * 54)}")
    print(
        f"  {hi('↵')} send again   "
        f"{hi('n')} new email   "
        f"{hi('q')} quit"
    )
    raw = input("  › ").strip().lower()
    return raw if raw in ("n", "q") else ""


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    print(f"\n  {hi('SMTP TESTER')}")

    srv, cfg = stage_connect()

    total, draft = 0, None
    try:
        while True:
            draft = compose(prev=draft)
            srv, sent = do_send(srv, cfg, draft)
            total += sent

            action = post_send_menu()
            if action == "q":
                break
            if action == "n":
                draft = None
    except KeyboardInterrupt:
        print("\n")
    finally:
        try: srv.quit()
        except Exception: pass

    print(f"\n{dim('·' * 54)}")
    print(field("sent", ok(str(total))))
    print()


if __name__ == "__main__":
    main()
