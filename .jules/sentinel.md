## 2025-05-22 - Terminal Command Chaining Bypass
**Vulnerability:** Command chaining using shell operators (`;`, `&&`, `||`, `|`, `&`) allowed executing unauthorized commands after an initial authorized one.
**Learning:** Initial validation only checked the base command or split by `|`, missing other common shell operators. `shlex.split` does not treat punctuation as separate tokens by default.
**Prevention:** Use `shlex.shlex` with `punctuation_chars=True` to robustly tokenize shell commands and identify all sub-commands separated by operators for validation.
