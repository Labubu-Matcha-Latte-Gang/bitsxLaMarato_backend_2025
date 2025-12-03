# Copilot Custom Instructions for Code Review — Python / Flask API

## 🧰 Project Context  
- This is a REST API built with **Python** using **Flask**.  
- Testing is done with **pytest**.  
- All dependencies must be declared in `requirements.txt`.  
- The project follows Python style conventions: `snake_case` for functions/variables/methods, `PascalCase` for classes.  

These instructions tell Copilot (in code-review mode) how to evaluate pull requests to enforce our conventions, code quality, and project standards.

---

## ✅ Naming, Style & Structure Conventions

### 📝 Naming

- Use **snake_case** for function names, variable names, method names, and arguments.  
- Use **PascalCase** for class names.  
- For global constants (if any), adopt UPPER_SNAKE_CASE or follow whatever constant naming convention is used in the project.  
- Modules/packages (i.e. `.py` filenames) should be lowercase, with optional underscores for clarity if needed.  

### 📚 Imports & Organization

- Imports go at the top of each file.  
- Order imports as: standard library → third-party libraries → local/project modules.  
- Avoid wildcard imports. Use explicit imports.  

### 📄 Documentation & Docstrings

- All public functions, classes, and modules should have docstrings explaining: purpose, parameters, return value, side-effects, exceptions raised, etc.  
- Internal comments (for developers) may be in English.  
- Documentation that describes behavior exposed to external clients (API docs, payload schema descriptions, error messages, response messages, etc.) must follow the project language guidelines (see below).  

---

## 🌍 Internationalization / Language Conventions (internal vs external)

- Internal code identifiers (variables, functions, class names, internal comments) should be in **English**, following the naming/style rules above.  
- Any text exposed to the API’s consumers (endpoint docs, schema definitions, error messages, response messages, user-facing logs, etc.) must use **Catalan** (or the designated external language).  
- Internal technical docs and comments can remain in English — they are for developers.  

---

## 🧩 Code Quality, Design, Maintainability & Best Practices

When reviewing a PR, Copilot should check for:

1. **Functional correctness** — logic must make sense; no obvious errors or missing logic.  
2. **Readability and clarity** — code should be easy to read: meaningful names, no cryptic variables, clear flow, avoid “clever but obscure” tricks.  
3. **Modularity & reusability** — use functions/classes to avoid duplication; organize code so that functionality is well separated; avoid monolithic functions doing too much.  
4. **Extensibility & maintainability** — structure code so future changes are easy: clear separation of concerns, minimal coupling, clear abstractions.  
5. **Consistent documentation** — public interfaces (endpoints, classes, methods) documented with docstrings and API docs if relevant; external-facing text localized correctly; internal docs in English.  
6. **Adherence to style & conventions** — naming as per guidelines, proper import order, formatting, PEP-8–compatible style.  

---

## 🧪 Testing with pytest & Dependency Management

- Every newly added or modified functionality (endpoints, business logic, data transformations, validations, error conditions) must include corresponding tests using **pytest**.  
- Tests must cover normal cases **and edge cases**: invalid input, error conditions, boundary cases, unexpected input, schema validation, etc.  
- If a PR adds a new dependency, the dependency must be added in `requirements.txt`.  
- After installing dependencies (e.g. in a fresh virtual environment) and running tests, everything should pass without errors.  

---

## 🔐 Security, Secrets & Configuration

- No hard-coded credentials, secrets, tokens, passwords, or sensitive data in source code.  
- Configuration for sensitive values (database URIs, secret keys, tokens, passwords, external service credentials, etc.) must be loaded from environment variables or secure config files — not in code.  
- Avoid absolute paths tied to local environments or non-portable settings. All configurations should be environment-agnostic (use env vars, config files, or relative paths).  

---

## 📝 Pull Request & Commit Guidelines

- PR titles must be clear, concise, descriptive, preferably using imperative verbs: e.g. `add: ...`, `fix: ...`, `refactor: ...`, `docs: ...`, etc.  
- PR descriptions should summarize what changed, why, and what the expected impact is — especially if there are API changes, message changes, contract changes, i18n changes, or configuration updates.  
- Keep PRs focused and limited in scope whenever possible. Avoid huge PRs with unrelated changes; prefer small, incremental, well-scoped changes.  
- If a PR affects external API contract (endpoints, error messages, response formats), document clearly what changes and why — especially for clients using the API.  

---

## 🧑‍💻 How Copilot Should Behave as Code Reviewer

When analyzing a PR:

- If it detects violations of naming/style conventions, missing docstrings, misuse of language (mixing English/Catalan incorrectly), missing tests, hard-coded secrets or missing dependency updates — it should generate actionable comments pointing out the exact issues and suggesting corrections.  
- If a feature lacks adequate test coverage (missing edge cases, no tests for error conditions, or no tests at all), it should flag this as a deficiency.  
- If new dependencies are added but not declared in `requirements.txt`, it should warn about missing dependency declaration.  
- If secrets or sensitive data appear in code, it should flag as potential security risk.  
- If code passes all checks (style, naming, documentation, tests, security, i18n), it should be able to emit a summary approval comment highlighting the strengths: good naming, proper tests, clear docs, correct internationalization, etc.  
- In ambiguous cases (e.g. edge-cases not obviously covered, complex logic that may need more tests, possible security concerns), Copilot should mark the PR for manual human review — it should not pretend to guarantee correctness.  

---

## 🗂 Location & Usage of this File

- Save this file as `.github/copilot-instructions.md` at the root of the repository. 
- Copilot (in supported editors/environments) will automatically load and apply these instructions during code review or when generating code.  
- You can complement this with more specific instruction files (e.g. path-scoped or language-scoped) under `.github/instructions/` using glob patterns — but for now, this one file should cover the whole repo.

---

## 🎯 Summary of Priorities for Reviewing

When Copilot reviews a PR, the prioritized checklist should be:

1. Functional correctness and absence of logic errors.  
2. Security: no hard-coded secrets or unsafe configuration.  
3. Conventions: naming, style, documentation, i18n separation (English vs Catalan).  
4. Test coverage: pytest tests covering normal and edge cases.  
5. Code design: modularity, readability, maintainability, separation of concerns.  
6. Clean PR/commit strategy: clear title, description, minimal scope, dependency declarations, documentation of external changes (API contract, messages, i18n).  

