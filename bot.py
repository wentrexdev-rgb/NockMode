import asyncio
import os
import random
import time
from datetime import datetime, timezone, timedelta

from aiohttp import web
from aiogram import Bot, Dispatcher, F, Router
from aiogram.types import (
    Message, LabeledPrice, PreCheckoutQuery,
    InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
)
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer

TOKEN = "1780243280:044LckyLaJ8_K0STT0sd4ouvETONgRYUSPP"
API_BASE = "http://31.77.9.111:8081"
DEV = "@dick"
PORT = int(os.environ.get("PORT", 8080))

session = AiohttpSession(api=TelegramAPIServer.from_base(API_BASE))
bot = Bot(token=TOKEN, session=session)
dp = Dispatcher()
router = Router()
dp.include_router(router)

user_stats, notif_states, online_active = {}, {}, {}

CITY_OFFSETS = {
    "москва": 3, "moscow": 3, "спб": 3, "питер": 3, "санкт-петербург": 3,
    "екатеринбург": 5, "екб": 5, "ekaterinburg": 5,
    "новосибирск": 7, "novosibirsk": 7,
    "калининград": 2, "kaliningrad": 2,
    "самара": 4, "samara": 4,
    "омск": 6, "omsk": 6,
    "красноярск": 7, "krasnoyarsk": 7,
    "иркутск": 8, "irkutsk": 8,
    "якутск": 9, "yakutsk": 9,
    "владивосток": 10, "vladivostok": 10,
    "минск": 3, "minsk": 3,
    "киев": 2, "kiev": 2
}

auto_states = {}

def get_auto(uid):
    return auto_states.setdefault(uid, {
        "format": False, "troll": False, "afk": False,
        "mute": False, "antimute": False, "nick": False, 
        "time_mode": False, "reply": False, "city": "москва", 
        "status": "Online", "custom_nick": ""
    })

def get_stats(uid):
    return user_stats.setdefault(uid, {"commands": 0, "games": 0, "wins": 0, "messages": 0})

def add_stat(uid, key):
    s = get_stats(uid)
    s[key] = s.get(key, 0) + 1

leet_table = {"a": "4", "e": "3", "i": "1", "o": "0", "s": "5", "t": "7", "l": "|", "g": "9", "b": "8"}
def leet(t):
    return "".join(leet_table.get(c.lower(), c) for c in t)

sw = str.maketrans({
    ord('q'): 'й', ord('w'): 'ц', ord('e'): 'у', ord('r'): 'к', ord('t'): 'е', ord('y'): 'н',
    ord('u'): 'г', ord('i'): 'ш', ord('o'): 'щ', ord('p'): 'з', ord('a'): 'ф', ord('s'): 'ы',
    ord('d'): 'в', ord('f'): 'а', ord('g'): 'п', ord('h'): 'р', ord('j'): 'о', ord('k'): 'л',
    ord('l'): 'д', ord('z'): 'я', ord('x'): 'ч', ord('c'): 'с', ord('v'): 'м', ord('b'): 'и',
    ord('n'): 'т', ord('m'): 'ь', ord('Q'): 'Й', ord('W'): 'Ц', ord('E'): 'У', ord('R'): 'К',
    ord('T'): 'Е', ord('Y'): 'Н', ord('U'): 'Г', ord('I'): 'Ш', ord('O'): 'Щ', ord('P'): 'З',
    ord('A'): 'Ф', ord('S'): 'Ы', ord('D'): 'В', ord('F'): 'А', ord('G'): 'П', ord('H'): 'Р',
    ord('J'): 'О', ord('K'): 'Л', ord('L'): 'Д', ord('Z'): 'Я', ord('X'): 'Ч', ord('C'): 'С',
    ord('V'): 'М', ord('B'): 'И', ord('N'): 'Т', ord('M'): 'Ь',
})

def main_menu_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📊 Статистика", callback_data="menu_stats"),
            InlineKeyboardButton(text="🤡 Список команд", callback_data="menu_help")
        ],
        [
            InlineKeyboardButton(text="⚙️ Настройки", callback_data="menu_settings"),
            InlineKeyboardButton(text="🎲 Бросить кубик", callback_data="menu_dice")
        ]
    ])

def welcome(name):
    return (
        "╔══════════════════════════════╗\n"
        "        🤡 ClownMode Bot        \n"
        "╚══════════════════════════════╝\n\n"
        f"Привет, {name}! 👋\n\n"
        "Бизнес-бот нового поколения.\n"
        "Используй кнопки ниже для управления или команды через точку (.)"
    )

ALL_COMMANDS_TEXT = (
    "🤡 Справочник команд ClownMode:\n\n"
    "🔒 Модерация:\n"
    "├ .spam [текст] — повторить 10 раз\n"
    "├ .mute — авто-мут входящих (удаление)\n"
    "├ .unmute — выключить мут\n"
    "├ .antimute [on/off] — авто-подпись\n"
    "└ .afk [текст] — автоответ\n\n"
    "🪄 Текст и стиль:\n"
    "├ .bold / .italic / .mono [текст]\n"
    "├ .leet / .kawaii / .tsundere / .yandere [текст]\n"
    "├ .reverse / .ascii / .qr / .sw [текст]\n"
    "└ .type [текст] — печать по буквам\n\n"
    "🔥 Фан и Игры:\n"
    "├ .love — объемное сердце ❤️\n"
    "├ .slot / .dice / .flip — казино и кубик\n"
    "├ .rps [rock/scissors/paper] — камень-ножницы\n"
    "├ .8ball [вопрос] — шар судьбы\n"
    "├ .roll [NdN] — бросок кубиков\n"
    "├ .quote / .ship / .iq\n"
    "└ .cat / .nk\n\n"
    "👤 Профиль и Система:\n"
    "├ .status [текст] / .nick [текст]\n"
    "├ .time [on/off город] / .ping / .info\n"
    "└ .stats — твоя статистика\n"
)


# --- ОБРАБОТКА КОМАНД И СООБЩЕНИЙ ---

async def handle_command_logic(msg: Message, text: str, uid: int, is_business: bool, business_connection_id: str = None):
    parts = text.split(maxsplit=1)
    cmd = parts[0].lower()
    arg = parts[1] if len(parts) > 1 else ""
    
    add_stat(uid, "commands")
    add_stat(uid, "messages")
    user_state = get_auto(uid)

    async def send_reply(content, **kwargs):
        if is_business and business_connection_id:
            return await bot.send_message(chat_id=msg.chat.id, text=content, business_connection_id=business_connection_id, **kwargs)
        else:
            return await msg.answer(content, **kwargs)

    if cmd in ("/help", ".help", ".команды"):
        await send_reply(ALL_COMMANDS_TEXT)
    elif cmd == ".ping":
        t = time.time()
        m = await send_reply("🤡...")
        if m:
            await m.edit_text(f"🤡 Понг! {int((time.time() - t) * 1000)}мс")
    elif cmd == ".spam":
        if arg:
            for _ in range(10):
                await send_reply(arg)
        else:
            await send_reply("❌ Использование: .spam [текст]")
    elif cmd == ".mute":
        user_state["mute"] = True
        await send_reply("🔕 Авто-мут включен: входящие сообщения собеседника будут удаляться.")
    elif cmd == ".unmute":
        user_state["mute"] = False
        await send_reply("🔔 Авто-мут выключен.")
    elif cmd == ".antimute":
        if arg.lower() == "off":
            user_state["antimute"] = False
            await send_reply("🔴 Авто-подпись выключена.")
        else:
            user_state["antimute"] = True
            await send_reply("🟢 Авто-подпись включена.")
    elif cmd == ".status":
        if arg:
            user_state["status"] = arg
            await send_reply(f"✅ Статус обновлен: {arg}")
        else:
            await send_reply(f"📌 Текущий статус: {user_state.get('status', 'Online')}")
    elif cmd == ".nick":
        if arg:
            user_state["custom_nick"] = arg
            await send_reply(f"✅ Кастомный ник установлен: {arg}")
        else:
            await send_reply("❌ Использование: .nick [новое имя]")
    elif cmd == ".bold":
        if arg:
            await send_reply(f"<b>{arg}</b>", parse_mode="HTML")
        else:
            await send_reply("❌ .bold текст")
    elif cmd == ".italic":
        if arg:
            await send_reply(f"<i>{arg}</i>", parse_mode="HTML")
        else:
            await send_reply("❌ .italic текст")
    elif cmd == ".mono":
        if arg:
            await send_reply(f"<code>{arg}</code>", parse_mode="HTML")
        else:
            await send_reply("❌ .mono текст")
    elif cmd == ".leet":
        if arg:
            await send_reply(leet(arg))
        else:
            await send_reply("❌ .leet текст")
    elif cmd == ".kawaii":
        if arg:
            await send_reply(f"(◕‿◕✿) {arg} ✨")
        else:
            await send_reply("❌ .kawaii текст")
    elif cmd == ".tsundere":
        if arg:
            await send_reply(f"Б-бака! {arg}... Не думай что специально!")
        else:
            await send_reply("❌ .tsundere текст")
    elif cmd == ".yandere":
        if arg:
            await send_reply(f"Только для тебя 🔪 {arg} 💕")
        else:
            await send_reply("❌ .yandere текст")
    elif cmd == ".reverse":
        if arg:
            await send_reply(arg[::-1])
        else:
            await send_reply("❌ .reverse текст")
    elif cmd == ".ascii":
        if arg:
            await send_reply(f"```\n" + "\n".join(list(arg.upper())) + "\n```", parse_mode="Markdown")
        else:
            await send_reply("❌ .ascii текст")
    elif cmd == ".qr":
        if arg:
            qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=250x250&data={arg}"
            if is_business and business_connection_id:
                await bot.send_photo(chat_id=msg.chat.id, photo=qr_url, caption=f"📱 QR-код: {arg}", business_connection_id=business_connection_id)
            else:
                await msg.answer_photo(photo=qr_url, caption=f"📱 QR-код: {arg}")
        else:
            await send_reply("❌ Использование: .qr [текст или ссылка]")
    elif cmd == ".sw":
        if arg:
            await send_reply(arg.translate(sw))
        else:
            await send_reply("❌ .sw текст")
    elif cmd == ".type":
        if arg:
            m = await send_reply("▌")
            built = ""
            for ch in arg:
                built += ch
                try:
                    if m:
                        await m.edit_text(built + "▌")
                except Exception:
                    pass
                await asyncio.sleep(0.05)
            if m:
                await m.edit_text(built)
        else:
            await send_reply("❌ .type текст")
    elif cmd == ".love":
        frames = [
            "♥",
            "♥♥♥\n ♥♥♥",
            " ♥♥♥♥♥ \n♥♥♥♥♥♥♥\n  ♥♥♥♥♥",
            "♥♥♥♥♥♥\n      ♥♥♥\n             ♥",
            "♥♥♥♥♥♥♥♥♥\n  ♥♥♥♥♥♥♥\n    ♥♥♥\n     ♥",
            "💖 Л Ю Б Л Ю 💖\n♥♥♥♥♥♥   ♥♥♥♥♥♥\n  ♥♥♥♥♥♥♥♥♥\n    ♥♥♥♥♥\n      ♥"
        ]
        m = await send_reply(frames[0])
        for f in frames[1:]:
            await asyncio.sleep(0.35)
            try:
                if m:
                    await m.edit_text(f)
            except Exception:
                pass
    elif cmd == ".flip":
        await send_reply(random.choice(["🦅 ОРЁЛ!", "🪙 РЕШКА!"]))
    elif cmd == ".slot":
        add_stat(uid, "games")
        if is_business and business_connection_id:
            await bot.send_dice(chat_id=msg.chat.id, emoji="🎰", business_connection_id=business_connection_id)
        else:
            await msg.answer_dice(emoji="🎰")
    elif cmd == ".dice":
        if is_business and business_connection_id:
            await bot.send_dice(chat_id=msg.chat.id, emoji="🎲", business_connection_id=business_connection_id)
        else:
            await msg.answer_dice(emoji="🎲")
    elif cmd == ".8ball":
        if arg:
            ans = ["Да 🟢", "Нет 🔴", "Возможно 🤔", "Точно да ✨", "Ни за что 🚫", "Спроси позже ⏳", "Весьма вероятно 👍"]
            await send_reply(f"🎱 Шар говорит: {random.choice(ans)}")
        else:
            await send_reply("❌ Использование: .8ball [вопрос]")
    elif cmd == ".roll":
        try:
            if "d" in arg:
                count, sides = map(int, arg.split("d"))
                rolls = [random.randint(1, sides) for _ in range(min(count, 20))]
                await send_reply(f"🎲 Бросок {arg}: {rolls} (Сумма: {sum(rolls)})")
            else:
                await send_reply(f"🎲 Выпало: {random.randint(1, 6)}")
        except Exception:
            await send_reply(f"🎲 Выпало: {random.randint(1, 6)}")
    elif cmd == ".quote":
        quotes = [
            "«Единственный способ делать великую работу — любить то, что вы делаете.» — Стив Джобс",
            "«Жизнь — это то, что с вами случается, пока вы строите другие планы.» — Джон Леннон",
            "«Успех — это способность идти от неудачи к неудаче без потери энтузиазма.» — Уинстон Черчилль",
            "«Лучший способ предсказать будущее — изобрести его.» — Алан Кей"
        ]
        await send_reply(random.choice(quotes))
    elif cmd == ".ship":
        percent = random.randint(0, 100)
        await send_reply(f"💖 Совместимость: {percent}%\n{'❤️ Идеальная пара!' if percent > 75 else '💔 Есть над чем работать...'}")
    elif cmd == ".iq":
        iq = random.randint(40, 180)
        await send_reply(f"🧠 Твой уровень IQ: {iq}\n{'Гений! 🔬' if iq > 140 else 'Норм пацан 👍' if iq > 90 else 'Инфузория-туфелька 🦠'}")
    elif cmd == ".timer":
        try:
            mins = int(arg)
            await send_reply(f"⏱ Таймер запущен на {mins} мин.")
            async def run_timer(chat_id, minutes):
                await asyncio.sleep(minutes * 60)
                await bot.send_message(chat_id, f"⏰ Время вышло! ({minutes} мин.)")
            asyncio.create_task(run_timer(msg.chat.id, mins))
        except Exception:
            await send_reply("❌ Использование: .timer [минуты числами]")
    elif cmd == ".poll":
        if arg:
            if is_business and business_connection_id:
                await bot.send_poll(chat_id=msg.chat.id, question=arg, options=["Да 👍", "Нет 👎", "Возможно 🤔"], business_connection_id=business_connection_id)
            else:
                await bot.send_poll(chat_id=msg.chat.id, question=arg, options=["Да 👍", "Нет 👎", "Возможно 🤔"])
        else:
            await send_reply("❌ Использование: .poll [вопрос]")
    elif cmd == ".afk":
        await send_reply(f"💤 {msg.from_user.first_name} {arg or 'отошёл'}")
    elif cmd == ".info":
        u = msg.from_user
        await send_reply(f"🪪 Карточка\n\n👤 {u.full_name}\n🆔 {u.id}\n📛 @{u.username or '—'}\n🌍 {u.language_code or '—'}")
    elif cmd == ".stats":
        s = get_stats(uid)
        await send_reply(f"📊 Твоя статистика:\n\n🤡 Команд: {s['commands']}\n🎮 Игр: {s['games']}\n🏆 Побед: {s['wins']}\n💬 Сообщений: {s['messages']}")
    elif cmd == ".time":
        parts_time = arg.split(maxsplit=1)
        sub = parts_time[0].lower() if parts_time else ""
        city_arg = parts_time[1] if len(parts_time) > 1 else "москва"

        if sub == "on":
            city_key = city_arg.lower()
            if city_key in CITY_OFFSETS:
                user_state["city"] = city_key
                user_state["time_mode"] = True
                offset = CITY_OFFSETS[city_key]
                cur_time = (datetime.now(timezone.utc) + timedelta(hours=offset)).strftime('%H:%M')
                await send_reply(f"🕐 Режим времени активирован для города {city_arg.capitalize()} [{cur_time}]")
            else:
                await send_reply("❌ Неизвестный город.")
        elif sub == "off":
            user_state["time_mode"] = False
            await send_reply("🕐 Режим времени выключен.")
        else:
            city = user_state.get("city", "москва")
            offset = CITY_OFFSETS.get(city, 3)
            cur_time = (datetime.now(timezone.utc) + timedelta(hours=offset)).strftime('%H:%M')
            await send_reply(f"🕐 Текущее время ({city.capitalize()}): [{cur_time}]")
    elif cmd == ".cat":
        await send_reply("🐱 https://cataas.com/cat")
    elif cmd == ".nk":
        await send_reply("🐱 няяя~ (◕‿◕✿)")
    elif cmd == ".rps":
        choice = arg.lower().strip()
        if choice not in ("rock", "scissors", "paper", "камень", "ножницы", "бумага"):
            await send_reply("✊ Использование: .rps rock (или scissors / paper)")
            return
        mapping = {"камень": "rock", "ножницы": "scissors", "бумага": "paper"}
        choice = mapping.get(choice, choice)
        ai = random.choice(["rock", "scissors", "paper"])
        labels = {"rock": "✊", "scissors": "✌️", "paper": "🖐"}
        wins = {"rock": "scissors", "scissors": "paper", "paper": "rock"}
        if choice == ai:
            res = "🤝 Ничья!"
        elif wins[choice] == ai:
            res = "🏆 Победа!"
            add_stat(uid, "wins")
        else:
            res = "💀 Проигрыш..."
        add_stat(uid, "games")
        await send_reply(f"Ты {labels[choice]} vs Бот {labels[ai]}\n\n{res}")
    else:
        await send_reply(f"❓ Неизвестная команда: {cmd}")


# --- BUSINESS MESSAGE HANDLER ---
@router.business_message()
async def business_msg_handler(msg: Message):
    if not msg.outgoing:
        uid = msg.from_user.id if msg.from_user else 0
        state = get_auto(uid)
        if state.get("mute", False):
            try:
                await bot.delete_business_message(
                    business_connection_id=msg.business_connection_id,
                    message_id=msg.message_id
                )
            except Exception:
                pass
        return

    uid = msg.from_user.id if msg.from_user else 0
    if msg.text and msg.text.startswith("."):
        try:
            await bot.delete_business_message(
                business_connection_id=msg.business_connection_id,
                message_id=msg.message_id
            )
        except Exception:
            pass
        
        try:
            await handle_command_logic(msg, msg.text, uid, is_business=True, business_connection_id=msg.business_connection_id)
        except Exception as e:
            print(f"Command execution error: {e}")
        return


# --- REGULAR MESSAGE & CALLBACK HANDLERS ---
@router.message(F.text.startswith("."))
async def dot_cmd_regular(msg: Message):
    uid = msg.from_user.id
    try:
        await handle_command_logic(msg, msg.text, uid, is_business=False)
    except Exception as e:
        print(f"Regular command error: {e}")


@router.message(F.text == "/start")
async def cmd_start_regular(msg: Message):
    await msg.answer(welcome(msg.from_user.first_name), reply_markup=main_menu_keyboard())


@router.message(F.text == "/help")
async def cmd_help_regular(msg: Message):
    await msg.answer(ALL_COMMANDS_TEXT)


@router.callback_query()
async def callback_handler(callback: CallbackQuery):
    data = callback.data
    uid = callback.from_user.id
    
    if data == "menu_stats":
        s = get_stats(uid)
        text = f"📊 Твоя статистика:\n\n🤡 Команд: {s['commands']}\n🎮 Игр: {s['games']}\n🏆 Побед: {s['wins']}\n💬 Сообщений: {s['messages']}"
        await callback.message.answer(text)
    elif data == "menu_help":
        await callback.message.answer(ALL_COMMANDS_TEXT)
    elif data == "menu_settings":
        state = get_auto(uid)
        text = f"⚙️ Твои настройки:\n\n🔕 Авто-мут: {'Вкл' if state['mute'] else 'Выкл'}\n🟢 Авто-подпись: {'Вкл' if state['antimute'] else 'Выкл'}\n📌 Статус: {state['status']}"
        await callback.message.answer(text)
    elif data == "menu_dice":
        await callback.message.answer_dice(emoji="🎲")
    
    await callback.answer()


@dp.pre_checkout_query()
async def pre_checkout(q: PreCheckoutQuery):
    await q.answer(ok=True)


@dp.message(F.successful_payment)
async def on_payment(msg: Message):
    await msg.answer(f"💙 Спасибо за {msg.successful_payment.total_amount} ⭐️!\nЭто мотивирует развивать ClownMode 🤡\n— {DEV}")


async def health(request):
    return web.Response(text="🤡 ClownMode alive")


async def main():
    app = web.Application()
    app.router.add_get("/", health)
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", PORT).start()
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
