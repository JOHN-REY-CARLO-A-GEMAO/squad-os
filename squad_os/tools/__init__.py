from squad_os.tools.registry import (
    WebSearchTool, FileWriterTool, ReadFileTool, TerminalTool, PythonRunnerTool,
    DashboardApprovalTool, MemorySearchTool, SetSharedValueTool, GetSharedValueTool,
    DelegateTaskTool, CommitProjectTool
)
from squad_os.tools.visual import BrowserControlTool, VisionAnalysisTool

from squad_os.tools.desktop import DesktopControlTool
from squad_os.tools.store import BrowseStoreTool, InstallPackageTool, RunWorkflowTool, UninstallPackageTool

from squad_os.tools.mcp_hub import MCPWrapperTool, MCPListTool, MCPRegisterTool
from squad_os.tools.media import ImageGenTool, VideoGenTool, NeuralAudioTool, AdvancedVideoEditorTool
from squad_os.tools.system import SystemMonitorTool, SystemSummaryTool
from squad_os.tools.sync import SquadDiscoverTool, SquadBlackboardTool, SquadResourceTool
from squad_os.tools.compute import ComputeDelegateTool, ComputeStatusTool, GPUInfoTool
from squad_os.tools.evolution import EvolutionTool