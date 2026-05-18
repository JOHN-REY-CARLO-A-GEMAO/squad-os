import asyncio
import os
import tempfile
import shutil
from squad_os.core.sandbox import DockerExecutor, SandboxConfig, SandboxResult, _check_docker


async def test_docker_availability():
    print("\nStarting Docker sandbox tests...")

    docker_available = await _check_docker()
    print(f"Docker available: {docker_available}")

    if not docker_available:
        print("⚠️  Docker not available — testing fallback behavior only")
        # Test that fallback works
        executor = DockerExecutor()
        result = await executor.execute_command("echo hello")
        assert "hello" in result.stdout, f"Expected 'hello' in output, got: {result.stdout}"
        print("OK: Host fallback execution works")

        result = await executor.execute_python("print('hello from python')", filename="test.py")
        assert "hello from python" in result.stdout, f"Expected 'hello from python', got: {result.stdout}"
        print("OK: Host fallback Python execution works")

        print("All sandbox fallback tests passed!")
        return True

    print("✅ Docker detected — testing full sandbox isolation")

    try:
        print("Testing basic command execution in sandbox...")
        executor = DockerExecutor(SandboxConfig(
            image="alpine:3.19",
            timeout=10,
            memory_mb=256,
            cpus=0.5,
        ))
        result = await executor.execute_command("echo 'sandbox works'")
        assert result.success, f"Command failed: {result.stderr}"
        assert "sandbox works" in result.stdout, f"Expected 'sandbox works', got: {result.stdout}"
        print("OK: Command executed in sandbox")

        print("Testing network isolation...")
        result = await executor.execute_command("wget -q -O- https://example.com 2>&1 || echo 'network blocked'")
        # In network-isolated mode, wget should fail
        assert "network blocked" in result.stdout or result.exit_code != 0, "Network should be blocked"
        print("OK: Network isolation confirmed")

        print("Testing Python execution in sandbox...")
        py_executor = DockerExecutor(SandboxConfig(
            image="python:3.11-slim",
            timeout=10,
            memory_mb=256,
        ))
        result = await py_executor.execute_python("print('hello from container')", filename="test.py")
        assert result.success, f"Python execution failed: {result.stderr}"
        assert "hello from container" in result.stdout, f"Expected output, got: {result.stdout}"
        print("OK: Python executed in sandbox")

        print("Testing workspace mount...")
        tmp_dir = tempfile.mkdtemp(prefix="squad_test_workspace_")
        try:
            # Write a file via the sandbox
            result = await executor.execute_command("echo 'mounted' > /workspace/test_mount.txt", tmp_dir)
            assert result.success, f"Workspace write failed: {result.stderr}"

            # Verify file exists on host
            test_file = os.path.join(tmp_dir, "test_mount.txt")
            assert os.path.exists(test_file), "File should exist in mounted workspace"
            with open(test_file) as f:
                assert "mounted" in f.read()
            print("OK: Workspace mount works correctly")
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

        print("Testing timeout enforcement...")
        result = await executor.execute_command("sleep 30", config=SandboxConfig(timeout=2))
        assert result.timed_out, f"Expected timeout, got exit_code={result.exit_code}"
        print("OK: Timeout enforcement works")

        print("Testing resource limits (memory)...")
        # Try to allocate more memory than allowed (256MB limit)
        result = await py_executor.execute_python(
            "data = 'x' * (512 * 1024 * 1024); print('allocated 512MB')",
            filename="memory_hog.py",
            config=SandboxConfig(image="python:3.11-slim", timeout=10, memory_mb=256),
        )
        assert not result.success, "Should fail due to memory limit"
        print("OK: Memory limits enforced")

        print("Testing container cleanup (no hanging containers)...")
        proc = await asyncio.create_subprocess_exec(
            "docker", "ps", "-q",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        stdout, _ = await proc.communicate()
        containers = stdout.decode().strip().split("\n") if stdout else []
        # Filter out empty strings
        active = [c for c in containers if c.strip()]
        assert len(active) == 0, f"Expected no hanging containers, found: {active}"
        print("OK: No hanging containers after tests")

    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    print("All Docker sandbox tests passed!")
    return True


if __name__ == "__main__":
    success = asyncio.run(test_docker_availability())
    exit(0 if success else 1)
