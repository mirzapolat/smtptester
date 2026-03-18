# smtp tester

```bash
python smtp_tester.py
```

Requires Python 3.10+. Install `markdown` (`pip install markdown`) for `.md` body files to send as HTML.

## Flow

**Stage 1** — enter host, port, credentials. Mode is auto-detected (port 465 → SSL, 587 → STARTTLS).

**Stage 2** — compose and send. All fields default to the previous value on repeat sends.

After sending: **↵** resend · **n** new email · **q / Esc** quit

## Shortcuts

Prefix any `to` or `body` input with `@` to load from a file:

```
to    @recipients.txt
body  @email.md
```

Recipient files can be newline, comma, or semicolon separated. Body multiline input ends with **Ctrl+D**.
