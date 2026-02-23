import os
import logging
import asyncio
import hashlib
import hmac
from aiohttp import web
from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message, PreCheckoutQuery, InlineKeyboardMarkup,
    InlineKeyboardButton, WebAppInfo, LabeledPrice
)
from aiogram.filters import CommandStart

# ========================================
BOT_TOKEN = "8582897108:AAGm1JIPzUW1I_AN_J_BE4-h2Oc_wm0qWiU"
ADMIN_ID   = [7462001064, 7527727908, 7721018727, 8018675711]   # ← ЗАМЕНИ НА СВОЙ ID (узнай у @userinfobot)
WEBAPP_URL = "https://glittering-praline-eeb0c2.netlify.app"
PORT       = int(os.environ.get("PORT", 8080))
# ========================================

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)
bot = Bot(token=BOT_TOKEN)
dp  = Dispatcher()

ALL_ITEMS = {
    "p90":      {"name": "П90",              "stars": 10,  "emoji": "🔫"},
    "zs9":      {"name": "ЖС9",              "stars": 10,  "emoji": "🎯"},
    "avm":      {"name": "АВМ",              "stars": 15,  "emoji": "⚡"},
    "amr":      {"name": "АМР",              "stars": 15,  "emoji": "💥"},
    "mk":       {"name": "МК Вышка",         "stars": 15,  "emoji": "🗼"},
    "gold_gun": {"name": "Золотые оружия",   "stars": 30,  "emoji": "🏆"},
    "full6":    {"name": "Фулл6",            "stars": 30,  "emoji": "👥"},
    "full_gold":{"name": "Фулл Золото",      "stars": 50,  "emoji": "👑"},
    "esc_2m":   {"name": "Сопровождение 2М", "stars": 50,  "emoji": "🛡️"},
    "esc_4m":   {"name": "Сопровождение 4М", "stars": 100, "emoji": "🛡️"},
    "esc_6m":   {"name": "Сопровождение 6М", "stars": 180, "emoji": "🛡️"},
    "esc_8m":   {"name": "Сопровождение 8М", "stars": 250, "emoji": "🛡️"},
    "esc_10m":  {"name": "Сопровождение 10М","stars": 300, "emoji": "💎"},
}

CORS = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type',
}

async def create_invoice_handler(request):
    if request.method == 'OPTIONS':
        return web.Response(status=200, headers=CORS)
    try:
        body = await request.json()
    except:
        return web.json_response({'error': 'bad json'}, status=400, headers=CORS)

    item_id = body.get('item_id')
    user_id = body.get('user_id')
    item = ALL_ITEMS.get(item_id)
    if not item:
        return web.json_response({'error': 'item not found'}, status=404, headers=CORS)

    try:
        link = await bot.create_invoice_link(
            title=f"{item['emoji']} {item['name']}",
            description=f"LEDNIK SHOP: {item['name']}",
            payload=f"{item_id}:{user_id}",
            currency="XTR",
            prices=[LabeledPrice(label=item['name'], amount=item['stars'])],
        )
        log.info(f"Invoice: {item['name']} for user {user_id}")
        return web.json_response({'invoice_link': link}, headers=CORS)
    except Exception as e:
        log.error(f"Invoice error: {e}")
        return web.json_response({'error': str(e)}, status=500, headers=CORS)

@dp.message(CommandStart())
async def cmd_start(message: Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🛒 Открыть магазин", web_app=WebAppInfo(url=WEBAPP_URL))
    ]])
    await message.answer(
        "💀 *LEDNIK SHOP — PUBG Black Market*\n\nЖми кнопку — откроется магазин!\nОплата звёздами ⭐",
        parse_mode="Markdown", reply_markup=kb
    )

@dp.pre_checkout_query()
async def pre_checkout(query: PreCheckoutQuery):
    await query.answer(ok=True)

@dp.message(F.successful_payment)
async def on_paid(message: Message):
    p = message.successful_payment
    item_id = p.invoice_payload.split(':')[0]
    item = ALL_ITEMS.get(item_id, {"name": item_id, "emoji": "✅"})
    user = message.from_user

    await message.answer(
        f"✅ *Оплата прошла!*\n\n{item['emoji']} *{item['name']}*\n⭐ {p.total_amount} звёзд\n\n📦 Доставим за 1–24 часа.",
        parse_mode="Markdown"
    )
    try:
        await bot.send_message(
            ADMIN_ID,
            f"💰 *ПОКУПКА!*\n👤 {user.full_name} (@{user.username or '—'})\n🆔 `{user.id}`\n{item['emoji']} {item['name']}\n⭐ {p.total_amount} звёзд",
            parse_mode="Markdown"
        )
    except Exception as e:
        log.error(f"Admin notify: {e}")

async def main():
    app = web.Application()
    app.router.add_post('/create_invoice', create_invoice_handler)
    app.router.add_route('OPTIONS', '/create_invoice', create_invoice_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, '0.0.0.0', PORT).start()
    log.info(f"Server on port {PORT}")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
