from __future__ import annotations

from langbot_plugin.api.definition.components.common.event_listener import EventListener
from langbot_plugin.api.entities import context, events


class QQResponseForwarder(EventListener):
    async def initialize(self):
        await super().initialize()

        @self.handler(events.NormalMessageResponded)
        async def on_normal_message_responded(ctx: context.EventContext):
            service = getattr(self.plugin, "forward_service", None)
            if service is None:
                return

            await service.handle_response(ctx)
