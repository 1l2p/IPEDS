# Claude Code — General Preferences

## Languages
- Primary: **Python** and **R**
- Follow idiomatic conventions for each language (PEP 8 for Python, tidyverse style for R where applicable)

## Code Style
- **Well-documented**: include docstrings for functions/classes (Python: Google or NumPy style), inline comments for non-obvious logic
- Use clear, descriptive variable and function names — prefer clarity over brevity
- Keep functions focused and single-purpose

### Python specifics
- Use type hints for function signatures
- Prefer `pathlib` over `os.path`
- Use f-strings for string formatting
- Virtual environments assumed (`venv` or `conda`)

### R specifics
- Prefer `tidyverse` packages (`dplyr`, `ggplot2`, `tidyr`, etc.) unless base R is clearly better
- Use `<-` for assignment
- Pipe with `|>` (native) or `%>%` (magrittr) — be consistent within a file

## Workflow
- Read and understand existing code before suggesting modifications
- Prefer editing existing files over creating new ones
- Keep changes minimal and focused — avoid refactoring code that wasn't asked about
- Ask before making large structural changes that span multiple files

## Communication
- Be concise and direct
- No unnecessary praise or filler phrases
- Use plain text or GitHub-flavored Markdown in responses
