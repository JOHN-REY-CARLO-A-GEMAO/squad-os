import asyncio
import os
import aiosqlite
from squad_os.database.session import (
    init_db,
    create_mission,
)
import squad_os.database.session as session
from squad_os.core.snapshot import capture_snapshot, restore_snapshot
from squad_os.models.snapshot import MissionSnapshot, TaskPlanSnapshot
from squad_os.core.exceptions import AgentInterruptException, ToolRiskException
from squad_os.core.circuit_breaker import QualityCircuitBreaker, validate_output_quality
from squad_os.core.tool_risk import TOOL_RISK_MAP, RISK_LABELS, get_risk_tier, requires_approval, RiskTier
from squad_os.core.db_pool import retry_on_locked, AsyncDBPool

async def test_hitl_database():
    print("Starting HITL database tests...")

    # 1. Setup: Initialize DB
    await init_db()

    # Create a dummy mission for foreign key
    mission_id = await create_mission("Test HITL Mission")
    print(f"Created mission {mission_id}")

    try:
        print("Testing init_interrupts_table...")
        if hasattr(session, 'init_interrupts_table'):
            await session.init_interrupts_table()
            print("OK: init_interrupts_table exists and ran")
        else:
            print("FAIL: init_interrupts_table NOT implemented")
            raise AttributeError("init_interrupts_table not found")

        print("Testing create_interrupt...")
        if hasattr(session, 'create_interrupt'):
            interrupt_id = await session.create_interrupt(
                mission_id=mission_id,
                task_idx=1,
                context="Testing context",
                error_message="Testing error"
            )
            print(f"OK: create_interrupt created interrupt {interrupt_id}")
        else:
            print("FAIL: create_interrupt NOT implemented")
            raise AttributeError("create_interrupt not found")

        print("Testing get_pending_interrupt...")
        if hasattr(session, 'get_pending_interrupt'):
            interrupt = await session.get_pending_interrupt(mission_id)
            if interrupt and interrupt['mission_id'] == mission_id and interrupt['status'] == 'PENDING':
                print("OK: get_pending_interrupt retrieved correct pending interrupt")
            else:
                print("FAIL: get_pending_interrupt failed to retrieve pending interrupt")
                raise AssertionError("Could not retrieve created pending interrupt")
        else:
            print("FAIL: get_pending_interrupt NOT implemented")
            raise AttributeError("get_pending_interrupt not found")

        print("Testing update_interrupt_guidance...")
        if hasattr(session, 'update_interrupt_guidance'):
            # Get the interrupt_id from the retrieved interrupt
            interrupt_id = interrupt['id']
            await session.update_interrupt_guidance(interrupt_id, "User guidance here")

            # Verify it's resolved
            async with aiosqlite.connect("shared_memory.db") as db:
                db.row_factory = aiosqlite.Row
                async with db.execute("SELECT status, user_guidance FROM mission_interrupts WHERE id = ?", (interrupt_id,)) as cursor:
                    row = await cursor.fetchone()
                    if row['status'] == 'RESOLVED' and row['user_guidance'] == "User guidance here":
                        print("OK: update_interrupt_guidance worked")
                    else:
                        print(f"FAIL: update_interrupt_guidance failed: {row}")
                        raise AssertionError("Interrupt not resolved or guidance not updated")
        else:
            print("FAIL: update_interrupt_guidance NOT implemented")
            raise AttributeError("update_interrupt_guidance not found")

    except Exception as e:
        print(f"Test failed: {e}")
        return False

    print("All HITL tests passed!")
    return True

async def test_snapshot_capture_restore():
    print("\nStarting snapshot capture/restore tests...")

    await init_db()
    mission_id = await create_mission("Test Snapshot Mission")
    print(f"Created mission {mission_id}")

    try:
        print("Testing capture_snapshot...")
        fake_plan = [
            type("TaskPlan", (), {"description": "Research API", "assigned_agent_role": "Researcher"})(),
            type("TaskPlan", (), {"description": "Write report", "assigned_agent_role": "Writer"})(),
        ]
        fake_messages = [
            {"role": "system", "content": "You are a researcher."},
            {"role": "user", "content": "Research the API."},
            {"role": "assistant", "content": "I need human input on the scope."},
        ]
        interrupt_id = await capture_snapshot(
            mission_id=mission_id,
            goal="Test Snapshot Mission",
            plan_tasks=fake_plan,
            task_idx=1,
            current_task_desc="Write report",
            agent_role="Writer",
            messages=fake_messages,
            context="Previous task completed successfully.",
            backtrack_counts={"0": 0},
            total_iterations=3,
            reason="Agent requested clarification on report format",
            prompt_tokens=150,
            completion_tokens=80,
        )
        print(f"OK: capture_snapshot created interrupt {interrupt_id}")

        print("Testing restore_snapshot...")
        snapshot = await restore_snapshot(interrupt_id)
        assert isinstance(snapshot, MissionSnapshot), "restore_snapshot did not return MissionSnapshot"
        assert snapshot.mission_id == mission_id, f"mission_id mismatch: {snapshot.mission_id} != {mission_id}"
        assert snapshot.current_step_index == 1, f"task_idx mismatch: {snapshot.current_step_index} != 1"
        assert snapshot.agent_role == "Writer", f"agent_role mismatch: {snapshot.agent_role} != 'Writer'"
        assert snapshot.prompt_tokens == 150, f"prompt_tokens mismatch: {snapshot.prompt_tokens} != 150"
        assert len(snapshot.reasoning_trace) == 3, f"reasoning_trace length: {len(snapshot.reasoning_trace)} != 3"
        assert snapshot.reasoning_trace[0]["role"] == "system", "reasoning_trace[0] is not system message"
        assert len(snapshot.execution_plan) == 2, f"execution_plan length: {len(snapshot.execution_plan)} != 2"
        assert snapshot.execution_plan[0].description == "Research API", "execution_plan[0] description mismatch"
        print("OK: restore_snapshot returned valid MissionSnapshot with all fields intact")

        print("Testing AgentInterruptException...")
        exc = AgentInterruptException(
            reason="Stuck on ambiguous task",
            messages=[{"role": "user", "content": "Help"}],
            prompt_tokens=50,
            completion_tokens=20,
        )
        assert exc.reason == "Stuck on ambiguous task"
        assert len(exc.messages) == 1
        assert exc.prompt_tokens == 50
        print("OK: AgentInterruptException created and fields verified")

    except Exception as e:
        print(f"Test failed: {e}")
        return False

    print("All snapshot tests passed!")
    return True

async def test_circuit_breaker():
    print("\nStarting circuit breaker tests...")

    try:
        print("Testing validate_output_quality...")
        valid, reason = validate_output_quality("This is a valid output with enough content.")
        assert valid is True, f"Valid output rejected: {reason}"

        invalid, reason = validate_output_quality("")
        assert invalid is False, "Empty string should be invalid"
        assert reason == "Empty output"

        invalid, reason = validate_output_quality("abc")
        assert invalid is False, "Short output should be invalid"

        invalid, reason = validate_output_quality("Error: something broke")
        assert invalid is False, "Short error output should be invalid"

        invalid, reason = validate_output_quality("NONE")
        assert invalid is False, "Placeholder output should be invalid"
        print("OK: validate_output_quality works correctly")

        print("Testing QualityCircuitBreaker...")
        cb = QualityCircuitBreaker(failure_threshold=3)
        task_id = 999

        assert cb.is_open(task_id) is False, "Circuit should be closed initially"
        assert cb.get_failure_count(task_id) == 0

        count1 = cb.record_failure(task_id)
        assert count1 == 1
        assert cb.is_open(task_id) is False

        count2 = cb.record_failure(task_id)
        assert count2 == 2
        assert cb.is_open(task_id) is False

        count3 = cb.record_failure(task_id)
        assert count3 == 3
        assert cb.is_open(task_id) is True, "Circuit should be open after 3 failures"

        cb.record_success(task_id)
        assert cb.get_failure_count(task_id) == 0, "Success should reset counter"
        assert cb.is_open(task_id) is False
        print("OK: QualityCircuitBreaker works correctly")

        print("Testing snapshot includes quality_failure_count...")
        await init_db()
        mission_id = await create_mission("Test Circuit Breaker Mission")
        fake_plan = [
            type("TaskPlan", (), {"description": "Test task", "assigned_agent_role": "Tester"})(),
        ]
        interrupt_id = await capture_snapshot(
            mission_id=mission_id,
            goal="Test Circuit Breaker Mission",
            plan_tasks=fake_plan,
            task_idx=0,
            current_task_desc="Test task",
            agent_role="Tester",
            messages=[],
            context="Test context",
            backtrack_counts={},
            total_iterations=1,
            reason="Output quality circuit opened",
            error_message="3 consecutive failures",
            quality_failure_count=3,
        )
        snapshot = await restore_snapshot(interrupt_id)
        assert snapshot.quality_failure_count == 3, f"quality_failure_count mismatch: {snapshot.quality_failure_count} != 3"
        print("OK: Snapshot correctly stores quality_failure_count")

    except Exception as e:
        print(f"Test failed: {e}")
        return False

    print("All circuit breaker tests passed!")
    return True

async def test_tool_risk_taxonomy():
    print("\nStarting tool risk taxonomy tests...")

    try:
        print("Testing risk tier classification...")
        assert TOOL_RISK_MAP["web_search"] == RiskTier.T0_READ_ONLY
        assert TOOL_RISK_MAP["read_file"] == RiskTier.T0_READ_ONLY
        assert TOOL_RISK_MAP["get_shared_value"] == RiskTier.T0_READ_ONLY
        assert TOOL_RISK_MAP["memory_search"] == RiskTier.T0_READ_ONLY
        assert TOOL_RISK_MAP["write_file"] == RiskTier.T1_INTERNAL_REVERSIBLE
        assert TOOL_RISK_MAP["set_shared_value"] == RiskTier.T1_INTERNAL_REVERSIBLE
        assert TOOL_RISK_MAP["delegate_task"] == RiskTier.T2_REVERSIBLE_COSTLY
        assert TOOL_RISK_MAP["terminal"] == RiskTier.T3_EXTERNAL_IRREVERSIBLE
        assert TOOL_RISK_MAP["python_runner"] == RiskTier.T3_EXTERNAL_IRREVERSIBLE
        assert TOOL_RISK_MAP["commit_project"] == RiskTier.T4_DESTRUCTIVE_HIGH_STAKES
        assert TOOL_RISK_MAP["request_human_input"] == RiskTier.T1_INTERNAL_REVERSIBLE
        print("OK: All tool risk tiers correctly classified")

        print("Testing get_risk_tier and requires_approval...")
        assert get_risk_tier("web_search") == 0
        assert get_risk_tier("terminal") == 3
        assert get_risk_tier("commit_project") == 4
        assert get_risk_tier("unknown_tool") == 3, "Unknown tools should default to T3"
        assert requires_approval("web_search") is False
        assert requires_approval("write_file") is False
        assert requires_approval("delegate_task") is False
        assert requires_approval("terminal") is True
        assert requires_approval("commit_project") is True
        print("OK: get_risk_tier and requires_approval work correctly")

        print("Testing ToolRiskException...")
        exc = ToolRiskException(
            tool_name="terminal",
            tool_args={"command": "rm -rf workspace"},
            risk_tier=3,
            risk_label="External/Irreversible",
            messages=[{"role": "user", "content": "I need to clean up"}],
        )
        assert exc.tool_name == "terminal"
        assert exc.risk_tier == 3
        assert exc.risk_label == "External/Irreversible"
        assert exc.tool_args["command"] == "rm -rf workspace"
        assert "terminal" in str(exc)
        assert "Tier 3" in str(exc)
        print("OK: ToolRiskException captures all fields correctly")

        print("Testing snapshot with tool risk interrupt...")
        await init_db()
        mission_id = await create_mission("Test Tool Risk Mission")
        fake_plan = [
            type("TaskPlan", (), {"description": "Run cleanup", "assigned_agent_role": "Executor"})(),
        ]
        interrupt_id = await capture_snapshot(
            mission_id=mission_id,
            goal="Test Tool Risk Mission",
            plan_tasks=fake_plan,
            task_idx=0,
            current_task_desc="Run cleanup",
            agent_role="Executor",
            messages=[{"role": "user", "content": "I need to clean up"}],
            context="About to run terminal command",
            backtrack_counts={},
            total_iterations=1,
            reason="Tool approval required: terminal (Tier 3: External/Irreversible)",
            error_message='{"command": "rm -rf workspace"}',
        )
        snapshot = await restore_snapshot(interrupt_id)
        assert "Tool approval" in snapshot.interrupt_reason
        assert snapshot.error_message == '{"command": "rm -rf workspace"}'
        print("OK: Snapshot correctly captures tool approval interrupt")

    except Exception as e:
        print(f"Test failed: {e}")
        return False

    print("All tool risk taxonomy tests passed!")
    return True

async def test_db_pool_and_retry():
    print("\nStarting database pool and retry tests...")

    try:
        print("Testing retry_on_locked decorator...")
        call_count = 0

        @retry_on_locked(max_retries=3, initial_backoff=0.01)
        async def flaky_write():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                import aiosqlite
                raise aiosqlite.Error("database is locked")
            return "success"

        result = await flaky_write()
        assert result == "success", f"Expected 'success', got {result}"
        assert call_count == 3, f"Expected 3 calls, got {call_count}"
        print("OK: retry_on_locked retries on locked errors")

        print("Testing retry_on_locked passes through non-locked errors...")
        @retry_on_locked(max_retries=3, initial_backoff=0.01)
        async def always_fail_other():
            raise ValueError("not a locked error")

        try:
            await always_fail_other()
            assert False, "Should have raised ValueError"
        except ValueError:
            pass
        print("OK: retry_on_locked does not retry non-locked errors")

        print("Testing AsyncDBPool...")
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        pool = AsyncDBPool(db_path, pool_size=2)
        await pool.initialize()

        conn1 = await pool.acquire()
        conn2 = await pool.acquire()
        assert conn1 is not None
        assert conn2 is not None

        await conn1.execute("CREATE TABLE test_pool (id INTEGER PRIMARY KEY, val TEXT)")
        await conn1.commit()
        await conn1.execute("INSERT INTO test_pool (val) VALUES (?)", ("hello",))
        await conn1.commit()
        await pool.release(conn1)

        cursor = await conn2.execute("SELECT val FROM test_pool WHERE id = 1")
        row = await cursor.fetchone()
        assert row[0] == "hello", f"Expected 'hello', got {row[0]}"
        await pool.release(conn2)

        await pool.close_all()
        os.unlink(db_path)
        print("OK: AsyncDBPool manages connections correctly")

    except Exception as e:
        print(f"Test failed: {e}")
        return False

    print("All database pool and retry tests passed!")
    return True

if __name__ == "__main__":
    success = asyncio.run(test_hitl_database())
    snapshot_success = asyncio.run(test_snapshot_capture_restore())
    cb_success = asyncio.run(test_circuit_breaker())
    tier_success = asyncio.run(test_tool_risk_taxonomy())
    pool_success = asyncio.run(test_db_pool_and_retry())
    if not success or not snapshot_success or not cb_success or not tier_success or not pool_success:
        exit(1)
    exit(0)
