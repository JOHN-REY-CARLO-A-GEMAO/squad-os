import os
import json
import shutil
from squad_os.core.projects import ProjectBranch

def test_jsonl_logging():
    base_dir = "test_workspace"
    if os.path.exists(base_dir):
        shutil.rmtree(base_dir)

    branch_id = "test_logging"
    branch = ProjectBranch(branch_id, base_dir=base_dir)
    branch.fork()

    # Verify file extension
    assert branch.log_path.endswith(".jsonl")
    assert os.path.exists(branch.log_path)

    # Log some calls
    branch.log_tool_call("tool1", {"a": 1}, "res1")
    branch.log_tool_call("tool2", {"b": 2}, "res2")

    # Read back and verify
    logs = []
    with open(branch.log_path, "r") as f:
        for line in f:
            if line.strip():
                logs.append(json.loads(line))

    assert len(logs) == 2
    assert logs[0]["tool"] == "tool1"
    assert logs[1]["tool"] == "tool2"
    assert logs[0]["inputs"] == {"a": 1}
    assert logs[1]["output"] == "res2"

    print("Test JSONL Logging: PASSED")
    shutil.rmtree(base_dir)

if __name__ == "__main__":
    test_jsonl_logging()
