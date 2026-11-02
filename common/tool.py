from collections.abc import Generator
from typing import Any
from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage
from common.client import VeilStratClient

class ResearchTool(Tool):
    operation = ""
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        client = VeilStratClient(self.runtime.credentials.get("api_key", ""))
        result = client.invoke(self.operation, tool_parameters)
        yield self.create_json_message(result)
