import os

def is_safe_path(base_dir: str, path: str, follow_symlinks: bool = True) -> bool:
    """
    Checks if a path is contained within a base directory.
    Prevents path traversal attacks by resolving paths and ensuring
    the target path is within the base directory.

    If 'path' is absolute, it's checked directly.
    If 'path' is relative, it's joined with 'base_dir' and then checked.
    """
    if not base_dir:
        return False

    abs_base = os.path.realpath(base_dir) if follow_symlinks else os.path.abspath(base_dir)

    # If the path is absolute, check it directly.
    # Otherwise, join it with the base_dir to resolve it.
    if os.path.isabs(path):
        abs_target = os.path.realpath(path) if follow_symlinks else os.path.abspath(path)
    else:
        # Important: Join with base_dir first to define the root for the relative path
        abs_target = os.path.realpath(os.path.join(abs_base, path)) if follow_symlinks else os.path.abspath(os.path.join(abs_base, path))

    try:
        # Check if the resolved target path is under the resolved base directory
        return os.path.commonpath([abs_base, abs_target]) == abs_base
    except ValueError:
        return False
