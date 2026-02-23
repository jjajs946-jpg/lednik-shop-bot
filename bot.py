import os
import logging
import asyncio
from aiohttp import web
from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message, PreCheckoutQuery, InlineKeyboardMarkup,
    InlineKeyboardButton, WebAppInfo, LabeledPrice
)
from aiogram.filters import CommandStart

BOT_TOKEN = "8582897108:AAGm1JIPzUW1I_AN_J_BE4-h2Oc_wm0qWiU"
ADMIN_ID   = 123456789
WEBAPP_URL = "https://glittering-praline-eeb0c2.netlify.app"
PORT       = int(os.environ.get("PORT", 8080))

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)
bot = Bot(token=BOT_TOKEN)
dp  = Dispatcher()

ALL_ITEMS = {
    "p90":      {"name": "П90",              "stars": 10},
    "zs9":      {"name": "ЖС9",              "stars": 10},
    "avm":      {"name": "АВМ",              "stars": 15},
    "amr":      {"name": "АМР",              "stars": 15},
    "mk":       {"name": "МК Вышка",         "stars": 15},
    "gold_gun": {"name": "Золотые оружия",   "stars": 30},
    "full6":    {"name": "Фулл6",            "stars": 30},
    "full_gold":{"name": "Фулл Золото",      "stars": 50},
    "esc_2m":   {"name": "Сопровождение 2М", "stars": 50},
    "esc_4m":   {"name": "Сопровождение 4М", "stars": 100},
    "esc_6m":   {"name": "Сопровождение 6М", "stars": 180},
    "esc_8m":   {"name": "Сопровождение 8М", "stars": 250},
    "esc_10m":  {"name": "Сопровождение 10М","stars": 300},
}

async def handle_options(request):
    return web.Response(status=200, headers={
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'POST, OPTIONS, GET',
        'Access-Control-Allow-Headers': '*',
    })

async def create_invoice_handler(request):
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'POST, OPTIONS, GET',
        'Access-Control-Allow-Headers': '*',
    }

    if request.method == 'OPTIONS':
        return web.Response(status=200, headers=headers)

    try:
        body = await request.json()
        log.info(f"Request received: {body}")
    except Exception as e:
        log.error(f"Bad JSON: {e}")
        return web.json_response({'error': 'bad json'}, status=400, headers=headers)

    item_id = body.get('item_id')
    user_id = body.get('user_id')
    item = ALL_ITEMS.get(item_id)

    if not item:
        log.error(f"Item not found: {item_id}")
        return web.json_response({'error': 'item not found'}, status=404, headers=headers)

    try:
        link = await bot.create_invoice_link(
            title=item['name'],
            description=f"LEDNIK SHOP: {item['name']}",
            payload=f"{item_id}:{user_id}",
            currency="XTR",
            prices=[LabeledPrice(label=item['name'], amount=item['stars'])],
        )
        log.info(f"Invoice created: {item['name']} for {user_id}")
        return web.json_response({'invoice_link': link}, headers=headers)
    except Exception as e:
        log.error(f"Invoice error: {e}")
        return web.json_response({'error': str(e)}, status=500, headers=headers)

async def health(request):
    return web.Response(text="OK", headers={'Access-Control-Allow-Origin': '*'})

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
    item = ALL_ITEMS.get(item_id, {"name": item_id})
    user = message.from_user

    await message.answer(
        f"✅ *Оплата прошла!*\n\n*{item['name']}*\n⭐ {p.total_amount} звёзд\n\n📦 Доставим за 1–24 часа.",
        parse_mode="Markdown"
    )
    try:
        await bot.send_message(
            ADMIN_ID,
            f"💰 *ПОКУПКА!*\n👤 {user.full_name} (@{user.username or '—'})\n🆔 `{user.id}`\n{item['name']}\n⭐ {p.total_amount} звёзд",
            parse_mode="Markdown"
        )
    except Exception as e:
        log.error(f"Admin notify: {e}")

async def main():
    app = web.Application()
    app.router.add_get('/', health)
    app.router.add_post('/create_invoice', create_invoice_handler)
    app.router.add_route('OPTIONS', '/create_invoice', handle_options)

    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, '0.0.0.0', PORT).start()
    log.info(f"✅ Server started on port {PORT}")

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
