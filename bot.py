import sys
import time
import asyncio
from datetime import date, datetime
from pathlib import Path
import importlib.util
import pytz

from aiohttp import web
from pyrogram import idle, __version__
from pyrogram.raw.all import layer
import pyrogram.utils

from database.ia_filterdb import Media, Media2
from database.users_chats_db import db
from info import *
from utils import temp
from Script import script
from plugins import web_server, check_expired_premium
from Lucia.Bot import SilentX
from Lucia.Bot.clients import initialize_clients
from logging_helper import LOGGER

# ⏱️ Start time
botStartTime = time.time()

pyrogram.utils.MIN_CHANNEL_ID = -1009147483647


# 🔌 Plugin Loader
def silentx_plugins_handler(app, plugins_dir: str | Path = "plugins", package_name: str = "plugins") -> list[str]:
    plugins_dir = Path(plugins_dir)
    loaded_plugins: list[str] = []

    if not plugins_dir.exists():
        LOGGER.warning("Plugins Directory '%s' Does Not Exist.", plugins_dir)
        return loaded_plugins

    for file in sorted(plugins_dir.rglob("*.py")):
        if file.name == "__init__.py":
            continue

        rel_path = file.relative_to(plugins_dir).with_suffix("")
        import_path = package_name + ".".join([""] + list(rel_path.parts))

        try:
            spec = importlib.util.spec_from_file_location(import_path, file)
            if spec is None or spec.loader is None:
                continue

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            sys.modules[import_path] = module
            loaded_plugins.append(import_path)

            LOGGER.info("🔌 Loaded plugin: %s", import_path)

        except Exception as e:
            LOGGER.error(f"Failed To Import Plugin: {import_path} | {e}")

    return loaded_plugins


# 🚀 MAIN START FUNCTION
async def SilentXBotz_start():

    # 🔴 ENV CHECK
    if not API_ID or not API_HASH or not BOT_TOKEN:
        LOGGER.error("Missing API_ID / API_HASH / BOT_TOKEN")
        sys.exit(1)

    if MULTIPLE_DB and not DATABASE_URI2:
        LOGGER.error("DATABASE_URI2 missing while MULTIPLE_DB enabled")
        sys.exit(1)

    LOGGER.info("🚀 Starting Bot...")

    # 🤖 Start bot
    await SilentX.start()
    bot_info = await SilentX.get_me()
    SilentX.username = bot_info.username

    # 👥 Multi clients
    await initialize_clients()

    # 🔌 Load plugins
    plugins = silentx_plugins_handler(SilentX)
    LOGGER.info(f"✅ Plugins Loaded: {len(plugins)}")

    # 🚫 Banned users
    try:
        b_users, b_chats = await db.get_banned()
        temp.BANNED_USERS = b_users
        temp.BANNED_CHATS = b_chats
    except Exception as e:
        LOGGER.error(f"Banned fetch error: {e}")

    # 📂 DB indexes
    try:
        await Media.ensure_indexes()
        if MULTIPLE_DB:
            await Media2.ensure_indexes()
    except Exception as e:
        LOGGER.error(f"DB index error: {e}")

    # 👤 Bot info
    me = await SilentX.get_me()
    temp.ME = me.id
    temp.U_NAME = me.username
    temp.B_NAME = me.first_name
    temp.B_LINK = me.mention

    # 🔄 Premium checker
    SilentX.loop.create_task(check_expired_premium(SilentX))

    LOGGER.info(
        "%s started | Pyrofork v%s | Layer %s",
        me.first_name,
        __version__,
        layer,
    )

    LOGGER.info(script.LOGO)

    # 🕒 Restart log
    try:
        tz = pytz.timezone("Asia/Kolkata")
        now = datetime.now(tz)
        await SilentX.send_message(
            chat_id=LOG_CHANNEL,
            text=script.RESTART_TXT.format(
                temp.B_LINK,
                date.today(),
                now.strftime("%H:%M:%S")
            ),
        )
    except Exception as e:
        LOGGER.error(f"Restart log error: {e}")

    # 🌐 Web server (Render fix)
    app = web.AppRunner(await web_server())
    await app.setup()
    await web.TCPSite(app, "0.0.0.0", PORT).start()

    LOGGER.info(f"🌐 Web server running on port {PORT}")

    # 🔄 Idle
    await idle()


# ▶️ RUN
if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(SilentXBotz_start())
    except KeyboardInterrupt:
        LOGGER.info("👋 Bot Stopped")
