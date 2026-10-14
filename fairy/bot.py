"""Discord entry point with an offline configuration/dependency check."""
if __package__ in (None, ""):
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import argparse
import asyncio
import threading
from fairy.runtime.shutdown import install_stop_handlers, restore_handlers


async def serve(settings, create_bot):
    bot = create_bot(settings)
    stopped = asyncio.Event()
    loop = asyncio.get_running_loop()
    handlers = install_stop_handlers(stopped)

    def read_quit():
        import sys
        if sys.stdin is None:
            return
        for line in sys.stdin:
            if line.strip().lower() == "q":
                try:
                    loop.call_soon_threadsafe(stopped.set)
                except RuntimeError:
                    pass  # Startup may have failed and closed the event loop.
                return

    threading.Thread(target=read_quit, daemon=True).start()
    connection = asyncio.create_task(bot.start(settings.token), name="discord-connection")
    shutdown = asyncio.create_task(stopped.wait(), name="discord-shutdown")
    try:
        done, _ = await asyncio.wait((connection, shutdown), return_when=asyncio.FIRST_COMPLETED)
        if connection in done:
            await connection
    finally:
        connection.cancel()
        shutdown.cancel()
        await asyncio.gather(connection, shutdown, return_exceptions=True)
        try:
            await bot.close()
        finally:
            restore_handlers(handlers)


def check_configuration():
    from fairy.config.settings import BotSettings
    settings = BotSettings.from_env()
    if not settings.token:
        raise RuntimeError("Set TOKEN in the project .env before starting the bot")
    from fairy.discord_bot.app import create_bot
    import discord
    # Verify the native encoder without sending packets or logging into Discord.
    discord.opus.Encoder()
    return settings, create_bot


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Check offline; do not log into Discord")
    args = parser.parse_args(argv)
    settings, create_bot = check_configuration()
    if args.check:
        print("Discord dependencies, Opus and configuration are ready.")
        return 0

    asyncio.run(serve(settings, create_bot))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
