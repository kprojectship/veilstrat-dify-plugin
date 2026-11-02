from typing import Any
from dify_plugin import ToolProvider
from dify_plugin.errors.tool import ToolProviderCredentialValidationError
from common.client import VeilStratClient, VeilStratError

class VeilstratProvider(ToolProvider):
    def _validate_credentials(self, credentials: dict[str, Any]) -> None:
        try:
            client = VeilStratClient(credentials.get("api_key", ""))
            client.invoke("get_health", {})
            client.invoke("get_usage", {})
        except VeilStratError as error:
            raise ToolProviderCredentialValidationError(str(error)) from None
