"""Construct and run Fairy; imports never log into Discord."""
import discord
from discord.ext import commands
from fairy.config.settings import BotSettings
from fairy.voice.manager import VoiceSessionManager
from .commands import text, voice
from .events import register_events

class FairyBot(commands.Bot):
    def __init__(self, settings, **kwargs):
        super().__init__(**kwargs)
        self.settings = settings
        self.voice_manager = VoiceSessionManager()

    async def close(self):
        await self.voice_manager.close()
        await super().close()

def create_bot(settings=None):
    settings = settings or BotSettings.from_env()
    intents = discord.Intents.default()
    intents.message_content = True
    intents.voice_states = True
    bot = FairyBot(settings, command_prefix="!", intents=intents)
    text.register_commands(bot)
    voice.register_commands(bot)
    register_events(bot)
    return bot

def main():
    from fairy.bot import main as run
    return run()
