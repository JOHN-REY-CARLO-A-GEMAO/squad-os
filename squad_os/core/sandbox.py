import asyncio
import logging
import os
import shutil
import tempfile
from typing import Optional

logger = logging.getLogger(__name__)

_DOCKER_AVAILABLE: Optional[bool] = None


async def _check_docker() -> bool:
    """Check if Docker is available on the host."""
    global _DOCKER_AVAILABLE
    if _DOCKER_AVAILABLE is not None:
        return _DOCKER_AVAILABLE
    try:
        proc = await asyncio.create_subprocess_exec(
            "docker", "info",
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await proc.wait()
        _DOCKER_AVAILABLE = proc.returncode == 0
    except FileNotFoundError:
        _DOCKER_AVAILABLE = False
    return _DOCKER_AVAILABLE


class SandboxConfig:
    """Resource limits and isolation settings for sandboxed execution."""

    def __init__(
        self,
        image: str = "python:3.11-slim",
        timeout: int = 30,
        memory_mb: int = 512,
        cpus: float = 1.0,
        max_pids: int = 64,
        network_enabled: bool = False,
        read_only_fs: bool = False,
    ):
        self.image = image
        self.timeout = timeout
        self.memory_mb = memory_mb
        self.cpus = cpus
        self.max_pids = max_pids
        self.network_enabled = network_enabled
        self.read_only_fs = read_only_fs


class SandboxResult:
    """Result from a sandboxed execution."""

    def __init__(self, stdout: str, stderr: str, exit_code: int, timed_out: bool = False):
        self.stdout = stdout
        self.stderr = stderr
        self.exit_code = exit_code
        self.timed_out = timed_out

    @property
    def success(self) -> bool:
        return self.exit_code == 0 and not self.timed_out

    def __str__(self) -> str:
        parts = []
        if self.stdout:
            parts.append(f"STDOUT: {self.stdout}")
        if self.stderr:
            parts.append(f"STDERR: {self.stderr}")
        if self.timed_out:
            parts.append("TIMED OUT")
        if not parts:
            parts.append(f"Exit code: {self.exit_code}")
        return "\n".join(parts)


class DockerExecutor:
    """Execute commands and code inside an ephemeral Docker container.

    Provides strong isolation for T3/T4 tool execution by running each
    command in a disposable container with resource limits, optional
    network isolation, and automatic cleanup.

    Falls back to host execution if Docker is unavailable (with a warning).
    """

    DEFAULT_SHELL_IMAGE = "alpine:3.19"
    DEFAULT_PYTHON_IMAGE = "python:3.11-slim"

    def __init__(self, config: Optional[SandboxConfig] = None):
        self.config = config or SandboxConfig()
        self._docker_available: Optional[bool] = None

    async def _ensure_docker(self) -> bool:
        if self._docker_available is None:
            self._docker_available = await _check_docker()
        return self._docker_available

    async def execute_command(
        self,
        command: str,
        workspace: Optional[str] = None,
        config: Optional[SandboxConfig] = None,
    ) -> SandboxResult:
        """Execute a shell command inside an ephemeral container.

        Args:
            command: The shell command to execute.
            workspace: Host directory to mount as /workspace inside the container.
            config: Optional override for sandbox resource limits.

        Returns:
            SandboxResult with stdout, stderr, exit code.
        """
        cfg = config or self.config

        if not await self._ensure_docker():
            logger.warning(
                "Docker not available — falling back to host execution for command: %s",
                command[:100],
            )
            return await self._execute_on_host(command, workspace)

        image = cfg.image if cfg.image != self.config.image else self.DEFAULT_SHELL_IMAGE

        docker_args = ["docker", "run", "--rm"]

        # Resource limits
        docker_args.extend(["--memory", f"{cfg.memory_mb}m"])
        docker_args.extend(["--cpus", str(cfg.cpus)])
        docker_args.extend(["--pids-limit", str(cfg.max_pids)])

        # Network isolation
        if not cfg.network_enabled:
            docker_args.extend(["--network", "none"])

        # Read-only filesystem with tmpfs for /tmp and /var
        if cfg.read_only_fs:
            docker_args.append("--read-only")
            docker_args.extend(["--tmpfs", "/tmp:rw,noexec,nosuid,size=64m"])
            docker_args.extend(["--tmpfs", "/var/tmp:rw,noexec,nosuid,size=16m"])

        # Workspace mount
        if workspace and os.path.isdir(workspace):
            abs_workspace = os.path.realpath(workspace)
            docker_args.extend(["-v", f"{abs_workspace}:/workspace:rw"])
            docker_args.extend(["-w", "/workspace"])

        # Security: drop all capabilities, no privilege escalation
        docker_args.extend(["--cap-drop", "ALL"])
        docker_args.append("--no-new-privileges")

        # User: run as non-root
        docker_args.extend(["--user", "1000:1000"])

        # Image and command
        docker_args.append(image)
        docker_args.extend(["sh", "-c", command])

        return await self._run_container(docker_args, cfg.timeout)

    async def execute_python(
        self,
        code: str,
        workspace: Optional[str] = None,
        filename: str = "script.py",
        config: Optional[SandboxConfig] = None,
    ) -> SandboxResult:
        """Execute Python code inside an ephemeral container.

        Writes the code to a temporary file, copies it into the container,
        runs it, and captures the output.

        Args:
            code: The Python source code to execute.
            workspace: Host directory to mount as /workspace inside the container.
            filename: Name for the script file inside the container.
            config: Optional override for sandbox resource limits.

        Returns:
            SandboxResult with stdout, stderr, exit code.
        """
        cfg = config or self.config

        if not await self._ensure_docker():
            logger.warning(
                "Docker not available — falling back to host execution for Python script: %s",
                filename,
            )
            return await self._execute_python_on_host(code, workspace, filename)

        image = cfg.image if cfg.image != self.config.image else self.DEFAULT_PYTHON_IMAGE

        # Write code to a temp file
        tmp_dir = tempfile.mkdtemp(prefix="squad_sandbox_")
        script_path = os.path.join(tmp_dir, filename)
        try:
            with open(script_path, "w", encoding="utf-8") as f:
                f.write(code)

            docker_args = ["docker", "run", "--rm"]

            # Resource limits
            docker_args.extend(["--memory", f"{cfg.memory_mb}m"])
            docker_args.extend(["--cpus", str(cfg.cpus)])
            docker_args.extend(["--pids-limit", str(cfg.max_pids)])

            # Network isolation (Python execution typically doesn't need network)
            if not cfg.network_enabled:
                docker_args.extend(["--network", "none"])

            # Read-only filesystem with tmpfs
            if cfg.read_only_fs:
                docker_args.append("--read-only")
                docker_args.extend(["--tmpfs", "/tmp:rw,noexec,nosuid,size=64m"])

            # Mount the temp directory with the script (read-only)
            docker_args.extend(["-v", f"{tmp_dir}:/script:ro"])

            # Mount workspace for file I/O
            if workspace and os.path.isdir(workspace):
                abs_workspace = os.path.realpath(workspace)
                docker_args.extend(["-v", f"{abs_workspace}:/workspace:rw"])
                docker_args.extend(["-w", "/workspace"])

            # Security
            docker_args.extend(["--cap-drop", "ALL"])
            docker_args.append("--no-new-privileges")
            docker_args.extend(["--user", "1000:1000"])

            # Image and command
            docker_args.append(image)
            docker_args.extend(["python", f"/script/{filename}"])

            result = await self._run_container(docker_args, cfg.timeout)
            return result
        finally:
            # Clean up temp directory
            try:
                shutil.rmtree(tmp_dir, ignore_errors=True)
            except OSError:
                pass

    async def _run_container(self, docker_args: list[str], timeout: int) -> SandboxResult:
        """Run a Docker container and capture output."""
        try:
            proc = await asyncio.create_subprocess_exec(
                *docker_args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    proc.communicate(), timeout=timeout
                )
                timed_out = False
            except asyncio.TimeoutError:
                # Kill the container on timeout
                try:
                    proc.kill()
                except ProcessLookupError:
                    pass
                # Also force-remove any leftover container
                await self._cleanup_hanging_containers()
                stdout_bytes, stderr_bytes = b"", b"Execution timed out after {timeout}s"
                timed_out = True

            stdout = stdout_bytes.decode("utf-8", errors="replace").strip()
            stderr = stderr_bytes.decode("utf-8", errors="replace").strip()

            if timed_out:
                return SandboxResult(stdout=stdout, stderr=stderr, exit_code=-1, timed_out=True)

            return SandboxResult(
                stdout=stdout,
                stderr=stderr,
                exit_code=proc.returncode or 0,
            )
        except Exception as e:
            return SandboxResult(
                stdout="",
                stderr=f"Sandbox execution error: {e}",
                exit_code=-1,
            )

    async def _cleanup_hanging_containers(self):
        """Force-remove any containers that might be hanging from timed-out executions."""
        try:
            proc = await asyncio.create_subprocess_exec(
                "docker", "ps", "-q", "-f", "status=running",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
            )
            stdout, _ = await proc.communicate()
            if stdout:
                container_ids = stdout.decode().strip().split("\n")
                for cid in container_ids:
                    cid = cid.strip()
                    if cid:
                        await asyncio.create_subprocess_exec(
                            "docker", "rm", "-f", cid,
                            stdout=asyncio.subprocess.DEVNULL,
                            stderr=asyncio.subprocess.DEVNULL,
                        )
        except Exception:
            pass

    async def _execute_on_host(
        self, command: str, workspace: Optional[str] = None
    ) -> SandboxResult:
        """Fallback: execute command on host (Docker unavailable)."""
        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=workspace,
            )
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(), timeout=self.config.timeout
            )
            return SandboxResult(
                stdout=stdout_bytes.decode("utf-8", errors="replace").strip(),
                stderr=stderr_bytes.decode("utf-8", errors="replace").strip(),
                exit_code=proc.returncode or 0,
            )
        except asyncio.TimeoutError:
            try:
                proc.kill()
            except ProcessLookupError:
                pass
            return SandboxResult(
                stdout="",
                stderr=f"Execution timed out after {self.config.timeout}s",
                exit_code=-1,
                timed_out=True,
            )
        except Exception as e:
            return SandboxResult(stdout="", stderr=str(e), exit_code=-1)

    async def _execute_python_on_host(
        self, code: str, workspace: Optional[str] = None, filename: str = "script.py"
    ) -> SandboxResult:
        """Fallback: execute Python on host (Docker unavailable)."""
        tmp_dir = tempfile.mkdtemp(prefix="squad_sandbox_")
        script_path = os.path.join(tmp_dir, filename)
        try:
            with open(script_path, "w", encoding="utf-8") as f:
                f.write(code)
            proc = await asyncio.create_subprocess_exec(
                "python", script_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=workspace,
            )
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(), timeout=self.config.timeout
            )
            return SandboxResult(
                stdout=stdout_bytes.decode("utf-8", errors="replace").strip(),
                stderr=stderr_bytes.decode("utf-8", errors="replace").strip(),
                exit_code=proc.returncode or 0,
            )
        except asyncio.TimeoutError:
            try:
                proc.kill()
            except ProcessLookupError:
                pass
            return SandboxResult(
                stdout="",
                stderr=f"Execution timed out after {self.config.timeout}s",
                exit_code=-1,
                timed_out=True,
            )
        except Exception as e:
            return SandboxResult(stdout="", stderr=str(e), exit_code=-1)
        finally:
            try:
                shutil.rmtree(tmp_dir, ignore_errors=True)
            except OSError:
                pass
