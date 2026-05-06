## 2025-05-06 - Optimize directory traversal with os.scandir
**Learning:** Using `os.scandir()` instead of `os.listdir()` + `os.path.isdir()` (or `os.path.isfile()`) significantly reduces the number of system calls. `os.scandir()` returns `DirEntry` objects that carry file type information retrieved during the directory listing, avoiding redundant `stat` calls for each entry.
**Action:** Use `os.scandir()` for directory listings where file type or attributes are needed for filtering.
