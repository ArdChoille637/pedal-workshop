# Security Policy

## Supported versions

This project is in active development. Only the latest commit on `main` receives security fixes.

## API keys and credentials

- **Never commit** real API keys, passwords, or tokens
- Use `.env` (gitignored) for local secrets — see `.env.example` for the template
- The macOS app stores supplier API keys in the **Keychain** via `KeychainHelper` — they are never written to disk in plaintext
- `UserDefaults` is not used for any credential in the native app

## Reporting a vulnerability

If you discover a security vulnerability, please **do not** open a public GitHub Issue.

Email a description to the repository owner via the email on their GitHub profile. Include:
- What the vulnerability is
- Steps to reproduce
- Potential impact

You'll receive a response within 72 hours. If the issue is confirmed, a fix will be released and you'll be credited in the changelog (unless you prefer to remain anonymous).

## Known limitations

- The Python API server has no authentication — it is designed for **local use only** (localhost). Do not expose it to a public network without adding auth middleware.
- The SQLite database (`data/workshop.db`) is not encrypted. Do not store sensitive personal data in it.
- Schematic files are loaded by path from the local filesystem — path traversal is only possible for a user who already has local file access.
