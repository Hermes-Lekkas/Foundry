# Contributing to The Foundry

Thank you for your interest in contributing to The Foundry! We welcome contributions from the community and are grateful for your help in making this project better.

## Quick Start

1. **Fork** the repository
2. **Clone** your fork: `git clone https://github.com/yourusername/the-foundry.git`
3. **Install** dependencies: `./install.sh` (Linux/macOS) or `install.bat` (Windows)
4. **Run tests**: `pytest tests/`
5. **Make your changes**
6. **Submit a Pull Request**

## Open-Core Model

The Foundry uses an **open-core** licensing model. Understanding this is important before contributing:

### What This Means

- **Open Source (MIT License)**: Core infrastructure, APIs, UI components, basic training
- **Proprietary (Source-Available)**: SDCR, Model DNA, Security Engine, Advanced Constitutional AI

### Where to Contribute

We **actively welcome** contributions to:

| Area | License | Contribution Welcome |
|------|---------|---------------------|
| `foundry/orchestrator/` | MIT | ✅ Yes |
| `foundry/config/` | MIT | ✅ Yes |
| `foundry/training_core/` | MIT | ✅ Yes |
| `foundry/sandbox/` | MIT | ✅ Yes |
| `foundry/shared/` | MIT | ✅ Yes |
| `foundry/data_engine/` (basic) | MIT | ✅ Yes |
| `foundry/evaluator/` (basic) | MIT | ✅ Yes |
| `frontend/` | MIT | ✅ Yes |
| `tests/` | MIT | ✅ Yes |
| `foundry/reflection/` | Proprietary | ❌ No (view only) |
| `foundry/security/` | Proprietary | ❌ No (view only) |
| `foundry/models/dna.py` | Proprietary | ❌ No (view only) |

### How to Check File License

Look at the header of any file:

```python
# The Foundry - Open Core LLM Training Ecosystem
# Copyright (c) 2026 Hermes Lekkas
# 
# This file is part of the open-core release (MIT License).
# See LICENSE file for full terms.
```

**MIT = Open for contribution**

```python
# The Foundry - Proprietary Module
# Copyright (c) 2026 Hermes Lekkas
#
# This file is PROPRIETARY and SOURCE-AVAILABLE.
# You may view and use this code, but may not modify or redistribute it.
```

**Proprietary = View only, do not modify**

## Development Setup

### Prerequisites

- Python 3.10+
- Node.js 18+
- CUDA (optional, for GPU training)

### Backend Development

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# or: .venv\Scripts\activate  # Windows

# Install dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Run the server
foundry serve
```

### Frontend Development

```bash
cd frontend
npm install
npm run dev
```

## Contribution Guidelines

### Code Style

- **Python**: Follow PEP 8, use `ruff` for linting
- **TypeScript**: Use ESLint/Prettier configurations provided
- **Commits**: Use conventional commits (`feat:`, `fix:`, `docs:`, `test:`)

### Before Submitting

1. **Run tests**: `pytest tests/`
2. **Check types**: `mypy foundry/` (backend), `tsc --noEmit` (frontend)
3. **Lint**: `ruff check foundry/` (backend), `eslint src/` (frontend)
4. **Update docs**: If you change behavior, update README/docs

### Pull Request Process

1. **Create a branch**: `git checkout -b feature/your-feature-name`
2. **Make focused commits**: One logical change per commit
3. **Write clear messages**: Explain what and why, not how
4. **Include tests**: Especially for bug fixes
5. **Update CHANGELOG.md**: Add your changes under "Unreleased"

### PR Template

```markdown
## Description
Brief description of what this PR does.

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Documentation update
- [ ] Performance improvement
- [ ] Refactoring

## Testing
How did you test this? What cases did you cover?

## Checklist
- [ ] Tests pass (`pytest`)
- [ ] Code follows style guidelines
- [ ] Documentation updated (if needed)
- [ ] Only MIT-licensed files modified
```

## What We're Looking For

### High Priority

- **Windows/WSL2 improvements**: Better native Windows support
- **Documentation**: Tutorials, examples, API docs
- **Tests**: Increase coverage for edge cases
- **UI/UX**: Frontend improvements, accessibility
- **Performance**: Optimizations for large datasets

### Good First Issues

Look for issues labeled `good-first-issue` or `help-wanted`:

- Documentation improvements
- Adding test cases
- Bug fixes in open-core modules
- UI polish and responsiveness

## Code Review

All contributions go through code review. Expect:

- **Feedback within 48 hours** (usually sooner)
- **Constructive suggestions** for improvement
- **Discussion** on architectural decisions
- **Approval** when ready to merge

## Recognition

Contributors will be:

- Listed in `CONTRIBUTORS.md`
- Mentioned in release notes
- Credited in documentation (if significant contribution)

## Questions?

- **GitHub Discussions**: Use for design questions
- **Email**: hermeslekkasdev@gmail.com

## License

By contributing, you agree that your contributions will be licensed under the same license as the file you're modifying:

- **MIT License** for open-core files
- **Proprietary License** terms apply to proprietary files (contributions not accepted)

---

Thank you for helping make The Foundry better! 🚀
