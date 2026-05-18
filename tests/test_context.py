import asyncio
from squad_os.core.context import ContextManager, _count_messages, _estimate_token_count


async def test_context_manager():
    print("\nStarting Context Manager tests...")

    try:
        print("Testing basic message management...")
        ctx = ContextManager(max_history_turns=3, max_messages=10)
        ctx.add_message({"role": "system", "content": "You are a helpful assistant."})
        ctx.add_message({"role": "user", "content": "Hello!"})
        ctx.add_message({"role": "assistant", "content": "Hi there!"})

        messages = ctx.get_messages()
        assert len(messages) == 3, f"Expected 3 messages, got {len(messages)}"
        assert messages[0]["role"] == "system"
        print("OK: Basic message management works")

        print("Testing sliding window pruning...")
        ctx2 = ContextManager(max_history_turns=2, max_messages=10)
        ctx2.add_message({"role": "system", "content": "System prompt"})

        # Add 5 turns (10 messages: 5 assistant + 5 tool)
        for i in range(5):
            ctx2.add_message({"role": "assistant", "content": f"Assistant response {i}"})
            ctx2.add_message({"role": "tool", "content": f"Tool result {i}"})

        assert ctx2.turn_count() == 5, f"Expected 5 turns, got {ctx2.turn_count()}"
        ctx2.prune()

        messages = ctx2.get_messages()
        # Should have: system + last 2 turns (4 messages) + possibly some pruned summary
        assistant_count = sum(1 for m in messages if m["role"] == "assistant")
        assert assistant_count <= 2, f"Expected <= 2 assistant messages after pruning, got {assistant_count}"
        assert messages[0]["role"] == "system", "System prompt should always be preserved"
        print(f"OK: Sliding window pruning works (kept {assistant_count} turns)")

        print("Testing context summary generation...")
        ctx3 = ContextManager(max_history_turns=2, max_messages=8, summarize_older=True)
        ctx3.add_message({"role": "system", "content": "System prompt"})

        # Add 4 turns
        for i in range(4):
            ctx3.add_message({"role": "assistant", "content": f"Assistant turn {i} with some detail"})
            ctx3.add_message({"role": "tool", "content": f"Tool output {i}"})

        ctx3.prune()
        assert ctx3.summary != "", "Summary should be generated after pruning"
        assert "[assistant]" in ctx3.summary.lower(), "Summary should contain assistant messages"
        print(f"OK: Context summary generated ({len(ctx3.summary)} chars)")

        print("Testing context summary injection...")
        base_context = "Current task: analyze the data"
        enriched = ctx3.get_context_with_summary(base_context)
        assert "Compressed Conversation History" in enriched
        assert "Current task: analyze the data" in enriched
        print("OK: Context summary injection works")

        print("Testing max_messages enforcement...")
        ctx4 = ContextManager(max_history_turns=10, max_messages=5)
        ctx4.add_message({"role": "system", "content": "System"})
        for i in range(8):
            ctx4.add_message({"role": "assistant", "content": f"Msg {i}"})

        ctx4.prune()
        messages = ctx4.get_messages()
        assert len(messages) <= 5, f"Expected <= 5 messages, got {len(messages)}"
        assert messages[0]["role"] == "system", "System should be preserved"
        print(f"OK: Max messages enforced ({len(messages)} messages)")

        print("Testing token estimation...")
        ctx5 = ContextManager()
        ctx5.add_message({"role": "user", "content": "Hello world, this is a test message."})
        tokens = ctx5.estimated_token_count()
        assert tokens > 0, "Token count should be positive"
        print(f"OK: Token estimation works (~{tokens} tokens)")

        print("Testing reset...")
        ctx6 = ContextManager()
        ctx6.add_message({"role": "system", "content": "System"})
        ctx6.summary = "Some summary"
        ctx6.reset()
        assert ctx6.message_count() == 0, "Messages should be cleared"
        assert ctx6.summary == "", "Summary should be cleared"
        print("OK: Reset works")

        print("Testing resume from summary...")
        ctx7 = ContextManager(max_history_turns=2, max_messages=8)
        ctx7.add_message({"role": "system", "content": "System prompt"})
        for i in range(4):
            ctx7.add_message({"role": "assistant", "content": f"Turn {i}"})
            ctx7.add_message({"role": "tool", "content": f"Result {i}"})
        ctx7.prune()
        saved_summary = ctx7.summary

        # Simulate resume: create new context manager with saved summary
        ctx8 = ContextManager(max_history_turns=2, max_messages=8)
        ctx8.summary = saved_summary
        ctx8.add_message({"role": "system", "content": "System prompt"})
        ctx8.add_message({"role": "user", "content": ctx8.get_context_with_summary("Continue from where we left off")})

        messages = ctx8.get_messages()
        user_msg = [m for m in messages if m["role"] == "user"][0]
        assert "Compressed Conversation History" in user_msg["content"]
        print("OK: Resume from summary works")

    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    print("All Context Manager tests passed!")
    return True


if __name__ == "__main__":
    success = asyncio.run(test_context_manager())
    exit(0 if success else 1)
