"""
SkillMarketplaceTool — dynamic tool discovery, loading, and management.

Allows agents to:
- Browse available skills/tools in the marketplace
- Install new tools from the marketplace
- Get metadata about tool capabilities
- Dynamically load tools at runtime
"""
import asyncio
import importlib
import json
import os
import pkgutil
import sys
from typing import Optional, List, Dict, Any
from squad_os.tools.base import BaseTool


class SkillRegistry:
    """Central registry for all available tools/skills."""
    
    _instance = None
    _tools = {}
    _categories = {}
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
            cls._instance._discover_tools()
        return cls._instance
    
    def _discover_tools(self):
        """Discover all available tools in the squad_os.tools package + installed store packages."""
        import squad_os.tools
        for importer, modname, ispkg in pkgutil.iter_modules(squad_os.tools.__path__):
            if modname.startswith('_'):
                continue
            try:
                module = importlib.import_module(f"squad_os.tools.{modname}")
                self._scan_module(module, modname)
            except Exception as e:
                print(f"[ERR] [SkillRegistry]: Failed to load tool from {modname}: {e}")

        # Discover tools from installed .sqad packages
        try:
            from squad_os.store.loader import AgentPackageLoader
            for tools_dir in AgentPackageLoader.get_tool_discovery_paths():
                if not os.path.isdir(tools_dir):
                    continue
                for tf in os.listdir(tools_dir):
                    if not tf.endswith(".py") or tf.startswith("_"):
                        continue
                    module_name = tf[:-3]
                    try:
                        spec_name = f"squad_os.tools.pkg_{module_name}"
                        spec = importlib.util.spec_from_file_location(
                            spec_name,
                            os.path.join(tools_dir, tf)
                        )
                        if spec and spec.loader:
                            module = importlib.util.module_from_spec(spec)
                            sys.modules[spec_name] = module
                            spec.loader.exec_module(module)
                            prefix = os.path.basename(os.path.dirname(tools_dir))
                            package_id = prefix.split("__")[0] if "__" in prefix else prefix
                            self._scan_module(module, module_name, package_prefix=package_id)
                    except Exception as e:
                        print(f"[ERR] [SkillRegistry]: Failed to load package tool {module_name}: {e}")
        except ImportError:
            pass

        # Inject MCP native tools from all cached schemas
        self._inject_mcp_tools()

    def _inject_mcp_tools(self):
        """Build and register dynamic BaseTool instances for every cached MCP tool schema."""
        try:
            from squad_os.tools.mcp_hub import MCPAggregator
            agg = MCPAggregator.get_instance()
            agg.inject_native_tools()
        except ImportError:
            pass
        except Exception as e:
            print(f"  [MCP] Injection error: {e}")

    def _scan_module(self, module, modname: str, package_prefix: str = None):
        """Scan a module for BaseTool subclasses and register them."""
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if (isinstance(attr, type) and 
                issubclass(attr, BaseTool) and 
                attr != BaseTool and
                hasattr(attr, 'name')):
                try:
                    tool_instance = attr()
                    tool_name = tool_instance.name
                    if package_prefix:
                        tool_name = f"{package_prefix}.{tool_name}"
                    self._tools[tool_name] = {
                        "name": tool_name,
                        "description": tool_instance.description,
                        "category": getattr(tool_instance, 'category', 'general'),
                        "parameters": tool_instance.parameters,
                        "module": modname,
                        "class": attr_name,
                        "package": package_prefix
                    }
                    
                    category = getattr(tool_instance, 'category', 'general')
                    if category not in self._categories:
                        self._categories[category] = []
                    self._categories[category].append(tool_name)
                except Exception as e:
                    print(f"[ERR] [SkillRegistry]: Failed to instantiate tool {attr_name}: {e}")
    
    def list_tools(self, category: Optional[str] = None) -> List[Dict]:
        """List all available tools, optionally filtered by category."""
        if category:
            tool_names = self._categories.get(category, [])
            return [self._tools[name] for name in tool_names if name in self._tools]
        return list(self._tools.values())
    
    def register_dynamic(self, tool_class: type) -> str:
        """Register a dynamically-created tool class (e.g. from MCPNativeTool factory).

        The class must be a ``BaseTool`` subclass with a ``name`` attribute.
        Returns the registered tool name.
        """
        name = tool_class.name
        self._tools[name] = {
            "name": name,
            "description": tool_class.description,
            "category": getattr(tool_class, 'category', 'mcp'),
            "parameters": tool_class.parameters,
            "dynamic_class": tool_class,
        }
        cat = self._tools[name]["category"]
        if cat not in self._categories:
            self._categories[cat] = []
        if name not in self._categories[cat]:
            self._categories[cat].append(name)
        return name

    def get_tool(self, name: str) -> Optional[BaseTool]:
        """Get a tool instance by name, with bare-name fallback for package tools."""
        tool_info = self._tools.get(name)
        if not tool_info:
            for key, info in self._tools.items():
                if isinstance(info, dict) and info.get("package") and key.endswith(f".{name}"):
                    tool_info = info
                    break
        if not tool_info:
            return None

        # Dynamic class (e.g. MCP native tools) — instantiate directly
        dynamic_cls = tool_info.get("dynamic_class")
        if dynamic_cls:
            try:
                return dynamic_cls()
            except Exception as e:
                print(f"[ERR] [SkillRegistry]: Failed to instantiate dynamic tool {name}: {e}")
                return None

        try:
            modname = tool_info['module']
            if tool_info.get("package"):
                full_module = f"squad_os.tools.pkg_{modname}"
            else:
                full_module = f"squad_os.tools.{modname}"
            module = importlib.import_module(full_module)
            tool_class = getattr(module, tool_info['class'])
            return tool_class()
        except Exception as e:
            print(f"[ERR] [SkillRegistry]: Failed to instantiate tool {name}: {e}")
            return None
    
    def get_categories(self) -> List[str]:
        """List all available tool categories."""
        return list(self._categories.keys())
    
    def search_tools(self, query: str) -> List[Dict]:
        """Search tools by name or description."""
        query_lower = query.lower()
        results = []
        for name, info in self._tools.items():
            if query_lower in name.lower() or query_lower in info['description'].lower():
                results.append(info)
        return results


class SkillMarketplaceTool(BaseTool):
    name = "browse_marketplace"
    description = (
        "Browse the skill marketplace to discover available tools. "
        "Returns a list of tools with their names, descriptions, categories, and parameters. "
        "Use category filter to browse by category, or search query to find specific tools."
    )
    parameters = {
        "type": "object",
        "properties": {
            "category": {
                "type": "string",
                "description": "Filter by category (e.g., 'communication', 'browser', 'terminal')"
            },
            "search": {
                "type": "string",
                "description": "Search query to find tools by name or description"
            }
        },
        "required": []
    }
    category = "marketplace"

    async def execute(self, category: Optional[str] = None, search: Optional[str] = None) -> str:
        registry = SkillRegistry.get_instance()
        
        if search:
            results = registry.search_tools(search)
            if not results:
                return f"No tools found matching '{search}'."
            return json.dumps({
                "search_query": search,
                "results": results
            }, indent=2)
        
        if category:
            results = registry.list_tools(category)
            if not results:
                return f"No tools found in category '{category}'. Available categories: {registry.get_categories()}"
            return json.dumps({
                "category": category,
                "tools": results
            }, indent=2)
        
        # List all categories and tool counts
        categories = registry.get_categories()
        category_summary = {}
        for cat in categories:
            tools = registry.list_tools(cat)
            category_summary[cat] = len(tools)
        
        return json.dumps({
            "total_tools": len(registry.list_tools()),
            "categories": category_summary,
            "usage": "Use category=<name> or search=<query> to browse specific tools"
        }, indent=2)


class InstallSkillTool(BaseTool):
    name = "install_skill"
    description = (
        "Install a new tool from the marketplace into the current agent's tool inventory. "
        "The tool will be available for use in subsequent tasks. "
        "Specify the tool name to install."
    )
    parameters = {
        "type": "object",
        "properties": {
            "tool_name": {
                "type": "string",
                "description": "Name of the tool to install (e.g., 'send_telegram', 'web_search')"
            }
        },
        "required": ["tool_name"]
    }
    category = "marketplace"

    async def execute(self, tool_name: str) -> str:
        registry = SkillRegistry.get_instance()
        tool = registry.get_tool(tool_name)
        
        if not tool:
            available = [t['name'] for t in registry.list_tools()]
            return f"Tool '{tool_name}' not found. Available tools: {available[:20]}"
        
        # Tool is already available in the registry
        # In a full implementation, this would dynamically add to agent's inventory
        return f"Tool '{tool_name}' is available and ready to use. Name: {tool.name}, Description: {tool.description}"


class GetToolInfoTool(BaseTool):
    name = "get_tool_info"
    description = (
        "Get detailed information about a specific tool including its parameters, "
        "usage examples, and capabilities. Specify the tool name to get info."
    )
    parameters = {
        "type": "object",
        "properties": {
            "tool_name": {
                "type": "string",
                "description": "Name of the tool to get information about"
            }
        },
        "required": ["tool_name"]
    }
    category = "marketplace"

    async def execute(self, tool_name: str) -> str:
        registry = SkillRegistry.get_instance()
        tool_info = registry._tools.get(tool_name)
        
        if not tool_info:
            return f"Tool '{tool_name}' not found. Use browse_marketplace to see available tools."
        
        return json.dumps({
            "tool": tool_info,
            "usage_hint": f"Use this tool by calling it with the required parameters: {tool_info['parameters'].get('required', [])}"
        }, indent=2)
