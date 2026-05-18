from enum import IntEnum
from typing import Dict


class RiskTier(IntEnum):
    T0_READ_ONLY = 0
    T1_INTERNAL_REVERSIBLE = 1
    T2_REVERSIBLE_COSTLY = 2
    T3_EXTERNAL_IRREVERSIBLE = 3
    T4_DESTRUCTIVE_HIGH_STAKES = 4


RISK_LABELS: Dict[int, str] = {
    0: "Read-only",
    1: "Internal/Reversible",
    2: "Reversible/Costly",
    3: "External/Irreversible",
    4: "Destructive/High-Stakes",
}

TOOL_RISK_MAP: Dict[str, int] = {
    "web_search": RiskTier.T0_READ_ONLY,
    "read_file": RiskTier.T0_READ_ONLY,
    "get_shared_value": RiskTier.T0_READ_ONLY,
    "memory_search": RiskTier.T0_READ_ONLY,
    "write_file": RiskTier.T1_INTERNAL_REVERSIBLE,
    "set_shared_value": RiskTier.T1_INTERNAL_REVERSIBLE,
    "delegate_task": RiskTier.T2_REVERSIBLE_COSTLY,
    "terminal": RiskTier.T3_EXTERNAL_IRREVERSIBLE,
    "python_runner": RiskTier.T3_EXTERNAL_IRREVERSIBLE,
    "desktop_control": RiskTier.T3_EXTERNAL_IRREVERSIBLE,
    "browser_control": RiskTier.T3_EXTERNAL_IRREVERSIBLE,
    "inspect_element": RiskTier.T3_EXTERNAL_IRREVERSIBLE,
    "commit_project": RiskTier.T4_DESTRUCTIVE_HIGH_STAKES,
    "dashboard_approval": RiskTier.T3_EXTERNAL_IRREVERSIBLE,
    "request_human_input": RiskTier.T1_INTERNAL_REVERSIBLE,
}


def get_risk_tier(tool_name: str) -> int:
    return TOOL_RISK_MAP.get(tool_name, RiskTier.T3_EXTERNAL_IRREVERSIBLE)


def requires_approval(tool_name: str) -> bool:
    return get_risk_tier(tool_name) >= RiskTier.T3_EXTERNAL_IRREVERSIBLE
