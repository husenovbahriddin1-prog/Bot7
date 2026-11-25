import asyncio
import logging
import os
from datetime import datetime
from zoneinfo import ZoneInfo

from aiohttp import web
from aiogram import Bot, Dispatcher, F
from aiogram.enums import ChatType
from aiogram.filters import Command
from aiogram.types import Message
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config import settings
from db import Database
from analyzer import analyze_message
from reports import build_daily_report

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("buxprime")

db = Database(settings.database_url)
dp = Dispatcher()
bot: Bot | None = None


def is_admin(user_id: int | None) -> bool:
    return user_id is not None and user_id == settings.admin_id


async def send_admin(text: str):
    if bot:
        await bot.send_message(settings.admin_id, text, disable_web_page_preview=True)


@dp.message(Command("start"))
async def start_cmd(message: Message):
    if not is_admin(message.from_user.id if message.from_user else None):
        await message.answer("Bu bot faqat tizim administratori uchun.")
        return
    await message.answer(
        "Assalomu alaykum! <b>BuxPrime AI Controller</b> ishga tayyor.\\n\\n"
        "/groups — ulangan guruhlar\\n"
        "/report — barcha guruhlar bo‘yicha umumiy hisobot\\n"
        "/problems — ochiq muammolar\\n"
        "/questions — javobsiz savollar\\n"
        "/responsible — mas’ullar va vazifalar\\n"
        "/week — so‘nggi 7 kun tahlili\\n"
        "/help — yordam"
    )


@dp.message(Command("help"))
async def help_cmd(message: Message):
    if is_admin(message.from_user.id if message.from_user else None):
        await message.answer(
            "Buyruqlar: /groups, /report, /problems, /questions, "
            "/responsible, /week. Guruhga botni qo‘shing va Privacy Mode’ni "
            "BotFather’da o‘chiring. Bot guruhdagi oddiy matnli xabarlarni kuzatadi."
        )


@dp.message(Command("groups"))
async def groups_cmd(message: Message):
    if not is_admin(message.from_user.id if message.from_user else None):
        return
    groups = await db.list_groups()
    if not groups:
        await message.answer("Hozircha guruh topilmadi. Botni kerakli guruhlarga qo‘shing.")
        return
    lines = ["<b>Ulangan guruhlar:</b>"]
    for g in groups:
        lines.append(f"• {g['title']} (ID: <code>{g['chat_id']}</code>)")
    await message.answer("\\n".join(lines))


@dp.message(Command("report"))
async def report_cmd(message: Message):
    if not is_admin(message.from_user.id if message.from_user else None):
        return
    await message.answer("Barcha guruhlar tahlili tayyorlanmoqda...")
    report = await build_daily_report(db, days=1)
    await message.answer(report[:4000] or "Hisobot uchun ma’lumot yetarli emas.")


@dp.message(Command("week"))
async def week_cmd(message: Message):
    if not is_admin(message.from_user.id if message.from_user else None):
        return
    await message.answer("Haftalik tahlil tayyorlanmoqda...")
    report = await build_daily_report(db, days=7)
    await message.answer(report[:4000] or "Haftalik ma’lumot topilmadi.")


@dp.message(Command("problems"))
async def problems_cmd(message: Message):
    if not is_admin(message.from_user.id if message.from_user else None):
        return
    items = await db.list_open_issues()
    if not items:
        await message.answer("Ochiq muammolar topilmadi.")
        return
    lines = ["<b>Ochiq muammolar:</b>"]
    for x in items[:30]:
        lines.append(
            f"• <b>{x['group_title']}</b>: {x['title']}\\n"
            f"  Holat: {x['status']} | Mas’ul: {x['responsible'] or 'Aniqlanmagan'}"
        )
    await message.answer("\\n".join(lines)[:4000])


@dp.message(Command("questions"))
async def questions_cmd(message: Message):
    if not is_admin(message.from_user.id if message.from_user else None):
        return
    items = await db.list_open_questions()
    if not items:
        await message.answer("Javobsiz savollar topilmadi.")
        return
    lines = ["<b>Javobsiz savollar:</b>"]
    for x in items[:30]:
        lines.append(f"• <b>{x['group_title']}</b>: {x['question']}\\n  Kim so‘radi: {x['asked_by'] or 'Noma’lum'}")
    await message.answer("\\n".join(lines)[:4000])


@dp.message(Command("responsible"))
async def responsible_cmd(message: Message):
    if not is_admin(message.from_user.id if message.from_user else None):
        return
    items = await db.list_responsibilities()
    if not items:
        await message.answer("Hozircha mas’uliyat biriktirilgan vazifalar yo‘q.")
        return
    lines = ["<b>Mas’ullar nazorati:</b>"]
    for x in items[:30]:
        lines.append(f"• {x['group_title']}: {x['title']} — {x['responsible'] or 'Aniqlanmagan'} ({x['status']})")
    await message.answer("\\n".join(lines)[:4000])


@dp.message(F.chat.type.in_({ChatType.GROUP, ChatType.SUPERGROUP}))
async def group_message_handler(message: Message):
    if not message.from_user or message.from_user.is_bot:
        return
    text = message.text or message.caption
    if not text or text.startswith("/"):
        return

    chat = message.chat
    user = message.from_user
    display_name = user.full_name or user.username or str(user.id)
    await db.upsert_group(chat.id, chat.title or "Nomsiz guruh")
    await db.save_message(
        chat_id=chat.id,
        message_id=message.message_id,
        user_id=user.id,
        user_name=display_name,
        text=text,
        sent_at=message.date,
    )

    # AI analysis is intentionally limited to text/captions to avoid treating
    # unsupported media as confirmed facts.
    try:
        context = await db.recent_messages(chat.id, limit=25)
        result = await analyze_message(
            group_title=chat.title or "Nomsiz guruh",
            author=display_name,
            current_text=text,
            context=context,
        )
        await db.apply_analysis(chat.id, chat.title or "Nomsiz guruh", result, display_name)
    except Exception:
        log.exception("Message analysis failed for chat %s", chat.id)


async def daily_report_job():
    try:
        report = await build_daily_report(db, days=1)
        if report:
            await send_admin("<b>BuxPrime — kunlik guruhlar tahlili</b>\\n\\n" + report[:3900])
    except Exception:
        log.exception("Daily report failed")


async def health(request):
    return web.json_response({"status": "ok", "service": "BuxPrime AI Controller"})


async def run_web():
    app = web.Application()
    app.router.add_get("/", health)
    app.router.add_get("/health", health)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", settings.port)
    await site.start()
    log.info("Health server listening on port %s", settings.port)
    return runner


async def main():
    global bot
    settings.validate()
    bot = Bot(token=settings.bot_token)
    await db.connect()
    await db.create_tables()

    scheduler = AsyncIOScheduler(timezone=ZoneInfo("Asia/Tashkent"))
    scheduler.add_job(daily_report_job, "cron", hour=18, minute=0)
    scheduler.start()

    runner = await run_web()
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        scheduler.shutdown(wait=False)
        await runner.cleanup()
        await db.close()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
