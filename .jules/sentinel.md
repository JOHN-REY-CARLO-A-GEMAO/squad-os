## 2025-05-22 - Path Traversal in Mission File Uploads

**Vulnerability:** The `Manager.run_mission` method was vulnerable to local file disclosure and potential data loss by moving arbitrary files from a user-provided `temp_path` in the `uploaded_files_json` metadata without validation.

**Learning:** Internal orchestration logic that processes file metadata (like "temporary paths" from a frontend or previous step) can be a vector for path traversal if it assumes the paths are safe. Security boundaries must be enforced at the point where these paths are used for system operations.

**Prevention:** Validate all file paths derived from user-supplied metadata against a strictly defined and resolved workspace directory using `is_safe_path` before performing any file system operations like `shutil.move` or `shutil.copy`.
