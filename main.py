from __future__ import annotations

from langbot_plugin.api.definition.plugin import BasePlugin

from qq_forward_limiter_plugin.service import QQForwardLimiterService


class QQForwardLimiterPlugin(BasePlugin):
    async def initialize(self) -> None:
        self.forward_service = QQForwardLimiterService(self)

    def __del__(self) -> None:
        service = getattr(self, "forward_service", None)
        if service is not None:
            service.close()
