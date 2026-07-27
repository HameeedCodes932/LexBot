# Contributing to LexBot

## Getting Started

1. Fork the repository.
2. Follow the [Installation Guide](INSTALL.md) to set up your local environment.
3. Create a feature branch: `git checkout -b feat/my-feature`
4. Make your changes.
5. Run linting and tests.
6. Push and open a PR.

## Code Style

- **Python**: Ruff (install via `pip install ruff`, run with `ruff check .`)
- **JavaScript/React**: ESLint + Prettier (run with `npx eslint . && npx prettier --check .`)
- All files must pass CI (ruff, pytest, eslint, vitest, Docker build) before merge.

## Pull Request Guidelines

- Keep PRs focused on a single concern.
- Write a clear title and description explaining what and why.
- Include tests for new features.
- Update relevant documentation (README, INSTALL, etc.) if the change affects usage.
- Reference any related issues.

## Commit Messages

Follow conventional commits:
- `feat:` — new feature
- `fix:` — bug fix
- `refactor:` — code restructuring
- `docs:` — documentation changes
- `test:` — adding/updating tests
- `chore:` — build/config changes

## Adding a New LLM Provider

1. Create `backend/providers/myprovider.py` implementing `BaseLLMProvider`.
2. Add the API key variable to `.env.example`.
3. Register in `backend/llm_provider.py` factory.
4. Add tests in `tests/test_llm.py`.

## Adding a New Frontend Route

1. Create the page component in `frontend/src/pages/`.
2. Add the route in `App.jsx` with `React.lazy`.
3. Add a nav link if needed.
4. Add E2E test in `frontend/e2e/app.spec.js`.

## Reporting Issues

Use the GitHub issue tracker. Include:
- Expected vs. actual behavior
- Steps to reproduce
- Environment (OS, browser, Python version, etc.)
- Relevant logs or error messages
