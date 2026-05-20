## 2026-05-20 - Syscall reduction via os.scandir()
**Learning:** `os.listdir()` combined with `os.path.isdir()` or `os.path.isfile()` creates O(2N) system calls because each entry requires a separate `stat` call to determine its type. `os.scandir()` returns `DirEntry` objects that bundle this metadata from the initial directory scan, reducing syscalls to O(N).
**Action:** Use `os.scandir()` as a context manager for all directory traversal and filtering tasks to achieve measurable performance gains (~7-8x in this environment).
