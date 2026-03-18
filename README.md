# smtp tester

Interactive CLI tool for testing SMTP servers. Connect once, send as many emails as you want without reconnecting.

## Requirements

Python 3.10+. No dependencies for plain text. Optionally:

```bash
pip install markdown   # enables HTML rendering for .md body files
```

## Usage

```bash
python smtp_tester.py
```

### Stage 1 — Connect

Enter your server credentials. The mode (SSL/STARTTLS/plain) is auto-detected from the port:

| Port | Mode |
|------|------|
| 465  | SSL/TLS |
| 587  | STARTTLS |
| other | prompted |

### Stage 2 — Compose & Send

| Field | Behavior |
|-------|----------|
| **from** | Display name |
| **address** | Sender email |
| **to** | Recipient(s) — see below |
| **subject** | Email subject |
| **body** | Email body — see below |

All fields remember the previous value as default. Press Enter to reuse.

#### Recipients

Type one or more addresses inline:

```
to   alice@example.com, bob@example.com
```

Prefix with `@` to load from a file:

```
to   @recipients.txt
```

The file can be newline-separated, comma-separated, or semicolon-separated.

#### Body

Press Enter on the body prompt to type multiline — finish with **Ctrl+D**:

```
body
         Hello,

         This is a test email.
         ^D
```

Start typing on the same line to use that as the first line, then Ctrl+D to finish.

Prefix with `@` to load from a file:

```
body   @message.txt
body   @newsletter.md
```

`.md` files are rendered to HTML (plain text fallback if `markdown` is not installed).

If you press Ctrl+D immediately without typing anything, the previous body is reused.

### After Sending

```
↵ send again    n new email    q quit
```

- **Enter** — resend the same email (same recipients, subject, body)
- **n** — compose a new email from scratch
- **q** — disconnect and exit

The connection stays open between sends. If it drops, the tool reconnects automatically before the next send.

## Recipient file format

Any mix of separators works:

```
alice@example.com
bob@example.com, carol@example.com
dave@example.com; eve@example.com
```
