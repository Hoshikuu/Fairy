"""Own sessions and voice locks for one bot instance."""
import asyncio

class VoiceSessionManager:
    def __init__(self):
        self.sessions = {}
        self.locks = {}
        self.whisper_lock = asyncio.Lock()

    def lock_for(self, guild_id):
        return self.locks.setdefault(guild_id, asyncio.Lock())

    async def stop(self, guild_id):
        session = self.sessions.pop(guild_id, None)
        if session is not None:
            await session.stop()

    async def close(self):
        await asyncio.gather(*(self.stop(guild_id) for guild_id in list(self.sessions)))
