# Contributing to Toolbank MCP + No-Bull Marketing

Thank you for your interest in contributing!

---

## Ways to Contribute

- **Bug reports** — open an issue using the Bug Report template
- **Feature requests** — open an issue using the Feature Request template
- **Tool harvest requests** — open an issue using the Tool Harvest Request template
- **Pull requests** — see the checklist below

---

## Development Setup

See [docs/DEVELOPMENT_GUIDE.md](docs/DEVELOPMENT_GUIDE.md) for full setup instructions.

---

## Pull Request Process

1. Fork the repository and create a branch from `main`
2. Make your changes, following the conventions in [docs/GUARDRAILS.md](docs/GUARDRAILS.md)
3. Run tests: `pytest tests/ -v`
4. Update `CHANGELOG.md` with your changes
5. Fill out the PR description template
6. Open a PR against `main`

---

## Code Style

- **Python**: PEP 8, type hints on all public functions, docstrings on public classes
- **JavaScript/JSX**: functional components, `"use client"` where needed, Tailwind-only styling

---

## Guardrails

Before submitting, review [docs/GUARDRAILS.md](docs/GUARDRAILS.md) and run the drift-detection checklist.

---

## Reporting Security Issues

Do **not** open a public issue for security vulnerabilities. Email the maintainer directly or use GitHub's private security advisory feature.
