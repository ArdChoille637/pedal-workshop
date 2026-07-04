# Security Policy

## Supported versions

Only the latest commit on `main` receives fixes.

## API keys and credentials

- **Never commit** real API keys, passwords, or tokens.
- The macOS app stores supplier API keys in the **Keychain** via
  `KeychainHelper` — never on disk in plaintext, never in `UserDefaults`.
- The pipeline reads any extraction API keys from **environment variables** —
  never hardcode them in a script.
- Use `.env` (gitignored) for local config; see `.env.example`.

## Reporting a vulnerability

Please **do not** open a public GitHub Issue. Email a description to the
repository owner via the email on their GitHub profile (what it is, steps to
reproduce, impact). You'll get a response within 72 hours.

## Notes

- Schematic files are loaded by local filesystem path; the app has no network
  server and no remote attack surface.
- The pipeline's derived data (`extractions/`, `pedal_schematics.db`,
  `kicad-projects/`) is user-local and gitignored — it is not redistributed.
