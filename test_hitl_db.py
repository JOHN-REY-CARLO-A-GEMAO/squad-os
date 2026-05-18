import asyncio
import os
import aiosqlite
from squad_os.database.session import (
    init_db,
    create_mission,
)
import squad_os.database.session as session

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

if __name__ == "__main__":
    success = asyncio.run(test_hitl_database())
    if not success:
        exit(1)
    exit(0)
