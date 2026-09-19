import asyncio
import os
import random
import time
from datetime import datetime, timezone, timedelta

from aiohttp import web
from aiogram import Bot, Dispatcher, F, Router
from aiogram.types import (
    Message, CallbackQuery, LabeledPrice, PreCheckoutQuery,
    InlineKeyboardMarkup, InlineKeyboardButton as Btn
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

ttt_games, rps_games, duel_games, bw_games = {}, {}, {}, {}
auto_states, user_stats, notif_states, online_active = {}, {}, {}, {}

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


def get_auto(uid):
    return auto_states.get(uid, {
        "format": False, "troll": False, "afk": False,
        "mute": False, "nick": False, "time_mode": False,
        "reply": False, "antimute_ping": False, "city": "москва", "status": "Online", "custom_nick": ""
    })


def toggle_auto(uid, key):
    s = get_auto(uid)
    s[key] = not s[key]
    auto_states[uid] = s
    return s


def get_stats(uid):
    return user_stats.get(uid, {"commands": 0, "games": 0, "wins": 0, "messages": 0})


def add_stat(uid, key):
    s = get_stats(uid)
    s[key] = s.get(key, 0) + 1
    user_stats[uid] = s


def mk(*rows):
    return InlineKeyboardMarkup(inline_keyboard=list(rows))


def row(*btns):
    return list(btns)


def b(text, cb=None, url=None):
    return Btn(text=text, callback_data=cb, url=url)


def back(to="main"):
    return mk(row(b("← Назад", to)))


def main_menu():
    return mk(
        row(b("📋 Команды", "cmd_menu"), b("🤖 Авто-режимы", "auto_menu")),
        row(b("🎮 Игры", "games_menu"), b("⚙️ Настройки", "settings_menu")),
        row(b("📊 Статистика", "stats"), b("ℹ️ О боте", "about")),
        row(b("📖 Туториал", "tutorial"), b("💙 Поддержать", "donate")),
    )


def cmd_kb():
    return mk(
        row(b("🔒 Модерация", "cmd_mod"), b("🪄 Текст", "cmd_text")),
        row(b("🔥 Фан", "cmd_fun"), b("🎮 Игры", "cmd_games")),
        row(b("🪪 Инфо", "cmd_info"), b("👤 Профиль", "cmd_profile")),
        row(b("🎨 Медиа", "cmd_media"), b("⚡️ Система", "cmd_system")),
        row(b("← Главное меню", "main")),
    )


def games_kb():
    return mk(
        row(b("❌ Крестики-нолики", "game_ttt"), b("✊ Камень-ножницы", "game_rps")),
        row(b("⚔️ Дуэль", "game_duel"), b("🎲 Кубик", "game_dice")),
        row(b("🪙 Монетка", "game_flip"), b("🔮 Предсказание", "game_fco")),
        row(b("⬛ Закрась поле", "game_bw")),
        row(b("← Назад", "main")),
    )


def ttt_kb(board):
    s = {"": "⬜", "X": "❌", "O": "⭕"}
    rows = []
    for i in range(3):
        rows.append([
            Btn(text=s[board[i * 3 + j]], callback_data="noop" if board[i * 3 + j] else f"ttt_{i * 3 + j}")
            for j in range(3)
        ])
    rows.append([b("🏳 Сдаться", "ttt_surrender")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def game_result_kb(replay):
    return mk(row(b("🔄 Реванш", replay), b("🏠 Меню", "games_menu")))


def rps_kb():
    return mk(row(b("✊", "rps_rock"), b("✌️", "rps_scissors"), b("🖐", "rps_paper")), row(b("🏳 Отмена", "games_menu")))


def duel_kb():
    return mk(
        row(b("🗡 Удар", "duel_hit"), b("🛡 Блок", "duel_block")),
        row(b("💨 Уклон", "duel_dodge"), b("💥 Крит x2", "duel_crit")),
        row(b("🏳 Сдаться", "duel_surrender")),
    )


def bw_kb(board):
    rows = []
    for i in range(5):
        rows.append([
            Btn(text="⬛" if board[i * 5 + j] else "⬜", callback_data="noop" if board[i * 5 + j] else f"bw_{i * 5 + j}")
            for j in range(5)
        ])
    rows.append([b("🔄 Сбросить", "game_bw"), b("🏠 Меню", "games_menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def donate_kb():
    return mk(
        row(b("⭐️ 15 звёзд", "donate_15"), b("⭐️ 25 звёзд", "donate_25")),
        row(b("⭐️ 50 звёзд", "donate_50"), b("⭐️ 100 звёзд", "donate_100")),
        row(b("← Назад", "main")),
    )


def auto_kb(uid):
    s = get_auto(uid)

    def t(key, label):
        return b(f"{'🟢' if s.get(key) else '🔴'} {label}", f"auto_{key}")

    return mk(
        row(t("format", "Авто-формат текста")),
        row(t("troll", "Авто-тролль")),
        row(t("afk", "AFK режим")),
        row(t("mute", "Авто-мут входящих")),
        row(t("nick", "Авто-имя (ник)")),
        row(t("time_mode", "Время в статусе/нике")),
        row(t("reply", "Авто-ответ")),
        row(t("antimute_ping", "Антимьют авто-пинг")),
        row(b("← Назад", "main")),
    )


def settings_kb(uid):
    notif = notif_states.get(uid, True)
    active = online_active.get(uid, False)
    return mk(
        row(b("🌍 Язык: 🇷🇺 RU", "noop")),
        row(b(f"🔔 Уведомления: {'ВКЛ' if notif else 'ВЫКЛ'}", "toggle_notif")),
        row(b(f"{'🟢' if active else '🔴'} Вечный онлайн", "online_toggle")),
        row(b("🗑 Очистить кэш", "clear_cache")),
        row(b("← Назад", "main")),
    )


def hearts(n):
    return "❤️" * n + "🖤" * (3 - n)


def check_ttt(bd):
    for a, c, d in [(0, 1, 2), (3, 4, 5), (6, 7, 8), (0, 3, 6), (1, 4, 7), (2, 5, 8), (0, 4, 8), (2, 4, 6)]:
        if bd[a] and bd[a] == bd[c] == bd[d]:
            return bd[a]


def leet(t):
    table = {"a": "4", "e": "3", "i": "1", "o": "0", "s": "5", "t": "7", "l": "|", "g": "9", "b": "8"}
    return "".join(table.get(c.lower(), c) for c in t)


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


def welcome(name):
    return (
        "╔══════════════════════════════╗\n"
        "        ⚡️ NockMode Bot        \n"
        "╚══════════════════════════════╝\n\n"
        f"Привет, {name}! 👋\n\n"
        "Бизнес-бот нового поколения.\n\n"
        "● Команды через точку — мгновенно\n"
        "● Игры прямо в кнопках\n"
        "● Авто-режимы — одной кнопкой\n"
        "● Без внешних API"
    )


def resolve_duel(p_action, ai_action):
    dmg_to_player = 0
    dmg_to_ai = 0

    if p_action == "hit":
        if ai_action not in ("block", "dodge"):
            dmg_to_ai = 1
    elif p_action == "crit":
        if ai_action not in ("block", "dodge"):
            dmg_to_ai = 2
        elif ai_action == "block":
            dmg_to_player += 1

    if ai_action == "hit":
        if p_action not in ("block", "dodge"):
            dmg_to_player = max(dmg_to_player, 1)
    elif ai_action == "crit":
        if p_action not in ("block", "dodge"):
            dmg_to_player = max(dmg_to_player, 2)
        elif ai_action == "block":
            dmg_to_ai += 1

    return dmg_to_player, dmg_to_ai


ALL_COMMANDS_TEXT = (
    "⚡️ **Интерактивное меню помощи NockMode**\n\n"
    "Выберите нужный раздел кнопками ниже или используйте команды через точку:"
)


@router.message(F.text.in_({"/start", "/help"}))
async def cmd_start(msg: Message):
    if msg.text == "/help":
        await msg.answer(ALL_COMMANDS_TEXT, reply_markup=cmd_kb(), parse_mode="Markdown")
    else:
        await msg.answer(welcome(msg.from_user.first_name), reply_markup=main_menu())


@router.callback_query(F.data == "main")
async def cb_main(c: CallbackQuery):
    await c.message.edit_text(welcome(c.from_user.first_name), reply_markup=main_menu())


@router.callback_query(F.data == "cmd_menu")
async def cb_cmd_menu(c: CallbackQuery):
    await c.message.edit_text("⚡️ NockMode — Команды\n\nВыбери раздел:", reply_markup=cmd_kb())


@router.callback_query(F.data == "games_menu")
async def cb_games_menu(c: CallbackQuery):
    await c.message.edit_text("🎮 Игры NockMode\n\nВыбери игру:", reply_markup=games_kb())


@router.callback_query(F.data == "tutorial")
async def cb_tutorial(c: CallbackQuery):
    text = (
        "📖 Как подключить NockMode\n\n"
        "1️⃣ Настройки → Business\n\n"
        "2️⃣ Раздел «Чат-боты»\n"
        "   → «Добавить бота»\n\n"
        "3️⃣ Найди @NockModeBot и добавь\n\n"
        "4️⃣ Разреши боту:\n"
        "   ● Читать сообщения\n"
        "   ● Отвечать за тебя\n\n"
        "5️⃣ Готово! Пиши .команды в чатах ⚡️\n\n"
        f"Вопросы: {DEV}"
    )
    await c.message.edit_text(text, reply_markup=back("main"))


@router.callback_query(F.data == "about")
async def cb_about(c: CallbackQuery):
    text = f"ℹ️ NockMode Bot\n\nВерсия: 1.2.0\nРазработчик: {DEV}\n\n⚡️ NockMode — быстрее. Чище. Лучше."
    kb = mk(row(b("👤 Разработчик", url="https://t.me/dick")), row(b("← Назад", "main")))
    await c.message.edit_text(text, reply_markup=kb)


@router.callback_query(F.data == "donate")
async def cb_donate(c: CallbackQuery):
    await c.message.edit_text("💙 Поддержать разработку\n\nВыбери сумму:", reply_markup=donate_kb())


@router.callback_query(F.data.startswith("donate_"))
async def cb_donate_pay(c: CallbackQuery):
    stars = int(c.data.split("_")[1])
    await c.bot.send_invoice(
        chat_id=c.from_user.id, title="💙 Поддержка NockMode",
        description=f"Спасибо за поддержку! ({stars} ⭐️)", payload=f"donate_{stars}",
        currency="XTR", prices=[LabeledPrice(label=f"⭐️ {stars} звёзд", amount=stars)]
    )
    await c.answer()


@router.callback_query(F.data == "stats")
async def cb_stats(c: CallbackQuery):
    s = get_stats(c.from_user.id)
    text = f"📊 Статистика\n\n⚡️ Команд: {s['commands']}\n🎮 Игр: {s['games']}\n🏆 Побед: {s['wins']}\n💬 Сообщений: {s['messages']}"
    await c.message.edit_text(text, reply_markup=mk(row(b("🔄 Обновить", "stats"), b("← Назад", "main"))))


@router.callback_query(F.data == "auto_menu")
async def cb_auto_menu(c: CallbackQuery):
    await c.message.edit_text("🤖 Авто-режимы\n\nНажми чтобы включить / выключить:", reply_markup=auto_kb(c.from_user.id))


@router.callback_query(F.data.startswith("auto_"))
async def cb_auto(c: CallbackQuery):
    toggle_auto(c.from_user.id, c.data[5:])
    await c.message.edit_reply_markup(reply_markup=auto_kb(c.from_user.id))
    await c.answer("✅ Переключено")


@router.callback_query(F.data == "settings_menu")
async def cb_settings(c: CallbackQuery):
    await c.message.edit_text("⚙️ Настройки NockMode", reply_markup=settings_kb(c.from_user.id))


@router.callback_query(F.data == "toggle_notif")
async def cb_toggle_notif(c: CallbackQuery):
    uid = c.from_user.id
    notif_states[uid] = not notif_states.get(uid, True)
    await c.message.edit_reply_markup(reply_markup=settings_kb(uid))
    await c.answer("🔔 Переключено")


@router.callback_query(F.data == "online_toggle")
async def cb_online_toggle(c: CallbackQuery):
    uid = c.from_user.id
    online_active[uid] = not online_active.get(uid, False)
    await c.message.edit_reply_markup(reply_markup=settings_kb(uid))
    if online_active[uid]:
        await c.answer("🟢 Вечный онлайн включён!", show_alert=True)
        asyncio.create_task(online_loop(uid))
    else:
        await c.answer("🔴 Выключен", show_alert=True)


async def online_loop(uid):
    while online_active.get(uid, False):
        try:
            await bot.get_me()
        except Exception as e:
            print(f"online error: {e}")
        await asyncio.sleep(15)


@router.callback_query(F.data == "clear_cache")
async def cb_clear_cache(c: CallbackQuery):
    uid = c.from_user.id
    for d in (ttt_games, rps_games, duel_games, bw_games):
        d.pop(uid, None)
    await c.answer("🗑 Кэш очищен!", show_alert=True)


@router.callback_query(F.data == "cmd_mod")
async def cb_cmd_mod(c: CallbackQuery):
    text = (
        "🔒 Модерация\n\n"
        "├ .spam [текст] — повторить 10 раз\n"
        "├ .mute — включить авто-мут входящих\n"
        "├ .unmute — выключить мут\n"
        "├ .antimute — пробить мьют\n"
        "├ .afk [текст] — автоответ\n"
        "├ .sw [текст] — смена раскладки\n"
        "├ .type [текст] — печать по буквам\n"
        "├ .zaebu — позвать в диалог\n"
        "└ .troll — ядовитый подкол"
    )
    await c.message.edit_text(text, reply_markup=back("cmd_menu"))


@router.callback_query(F.data == "cmd_text")
async def cb_cmd_text(c: CallbackQuery):
    text = (
        "🪄 Текст и стиль\n\n"
        "├ .bold / .italic / .mono\n"
        "├ .leet — l33t стиль\n"
        "├ .kawaii — каваии стиль\n"
        "├ .tsundere / .yandere\n"
        "├ .reverse — задом наперёд\n"
        "└ .ascii [текст] — ASCII арт"
    )
    await c.message.edit_text(text, reply_markup=back("cmd_menu"))


@router.callback_query(F.data == "cmd_fun")
async def cb_cmd_fun(c: CallbackQuery):
    await c.message.edit_text(
        "🔥 Фан\n\n├ .love — объемное сердце ❤️\n├ .flip — монетка\n├ .8ball — шар судьбы\n├ .roll — кубики\n└ .quote — цитата",
        reply_markup=back("cmd_menu")
    )


@router.callback_query(F.data == "cmd_games")
async def cb_cmd_games(c: CallbackQuery):
    await c.message.edit_text(
        "🎮 Игры\n\n├ .ttt — крестики-нолики\n├ .rps — камень-ножницы\n├ .duel — дуэль\n├ .dice — кубик\n└ .bw — закрась поле",
        reply_markup=back("cmd_menu")
    )


@router.callback_query(F.data == "cmd_info")
async def cb_cmd_info(c: CallbackQuery):
    await c.message.edit_text(
        "🪪 Инфо\n\n├ .info — карточка пользователя\n├ .clone — клон по реплаю\n└ .short [текст] — краткий пересказ",
        reply_markup=back("cmd_menu")
    )


@router.callback_query(F.data == "cmd_profile")
async def cb_cmd_profile(c: CallbackQuery):
    text = (
        "👤 Профиль\n\n"
        "├ .status [текст] — установить статус\n"
        "├ .nick [текст] — установить ник\n"
        "├ .time — текущее время\n"
        "├ .time on [город] — время в фамилии/нику\n"
        "├ .time off — выключить время\n"
        "└ .ping — задержка ⚡️"
    )
    await c.message.edit_text(text, reply_markup=back("cmd_menu"))


@router.callback_query(F.data == "cmd_media")
async def cb_cmd_media(c: CallbackQuery):
    await c.message.edit_text(
        "🎨 Медиа\n\n├ .circle — видеокружок\n├ .lq — сжать фото\n├ .story — 9 историй\n└ .nk — неко-тян 🐱",
        reply_markup=back("cmd_menu")
    )


@router.callback_query(F.data == "cmd_system")
async def cb_cmd_system(c: CallbackQuery):
    await c.message.edit_text("⚡️ Система\n\n├ .ping — задержка бота\n└ .check — инфо о файле", reply_markup=back("cmd_menu"))


@router.callback_query(F.data == "game_ttt")
async def cb_ttt_start(c: CallbackQuery):
    ttt_games[c.from_user.id] = [""] * 9
    await c.message.edit_text("❌ Крестики-нолики\n\nТвой ход:", reply_markup=ttt_kb(ttt_games[c.from_user.id]))


@router.callback_query(F.data.startswith("ttt_") & (F.data != "ttt_surrender"))
async def cb_ttt(c: CallbackQuery):
    uid = c.from_user.id
    if uid not in ttt_games:
        await c.answer("Начни заново", show_alert=True)
        return
    board = ttt_games[uid]
    board[int(c.data[4:])] = "X"
    if check_ttt(board):
        del ttt_games[uid]
        add_stat(uid, "wins")
        add_stat(uid, "games")
        await c.message.edit_text("🏆 Победа!", reply_markup=game_result_kb("game_ttt"))
        return
    if "" not in board:
        del ttt_games[uid]
        add_stat(uid, "games")
        await c.message.edit_text("🤝 Ничья!", reply_markup=game_result_kb("game_ttt"))
        return
    empty = [i for i, v in enumerate(board) if not v]
    board[random.choice(empty)] = "O"
    if check_ttt(board):
        del ttt_games[uid]
        add_stat(uid, "games")
        await c.message.edit_text("💀 Проигрыш...", reply_markup=game_result_kb("game_ttt"))
        return
    if "" not in board:
        del ttt_games[uid]
        add_stat(uid, "games")
        await c.message.edit_text("🤝 Ничья!", reply_markup=game_result_kb("game_ttt"))
        return
    await c.message.edit_text("❌ Твой ход:", reply_markup=ttt_kb(board))


@router.callback_query(F.data == "ttt_surrender")
async def cb_ttt_surrender(c: CallbackQuery):
    ttt_games.pop(c.from_user.id, None)
    await c.message.edit_text("🏳 Сдался.", reply_markup=game_result_kb("game_ttt"))


@router.callback_query(F.data == "game_rps")
async def cb_rps(c: CallbackQuery):
    await c.message.edit_text("✊ Выбери:", reply_markup=rps_kb())


@router.callback_query(F.data.startswith("rps_"))
async def cb_rps_move(c: CallbackQuery):
    uid = c.from_user.id
    choice = c.data[4:]
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
    await c.message.edit_text(f"Ты {labels[choice]} vs Бот {labels[ai]}\n\n{res}", reply_markup=game_result_kb("game_rps"))


@router.callback_query(F.data == "game_duel")
async def cb_duel(c: CallbackQuery):
    duel_games[c.from_user.id] = {"hp_p": 3, "hp_ai": 3}
    await c.message.edit_text(f"⚔️ Дуэль\n\nТы {hearts(3)} vs Противник {hearts(3)}\n\nВыбери:", reply_markup=duel_kb())


@router.callback_query(F.data.startswith("duel_") & (F.data != "duel_surrender"))
async def cb_duel_action(c: CallbackQuery):
    uid = c.from_user.id
    if uid not in duel_games:
        await c.answer("Начни заново", show_alert=True)
        return
    g = duel_games[uid]
    action = c.data[5:]
    ai = random.choice(["hit", "block", "dodge", "crit"])
    dmg_to_player, dmg_to_ai = resolve_duel(action, ai)
    g["hp_p"] = max(0, g["hp_p"] - dmg_to_player)
    g["hp_ai"] = max(0, g["hp_ai"] - dmg_to_ai)
    if g["hp_p"] <= 0:
        del duel_games[uid]
        add_stat(uid, "games")
        await c.message.edit_text(
            f"💀 Проигрыш!\n\nТы {hearts(0)} vs Противник {hearts(g['hp_ai'])}", reply_markup=game_result_kb("game_duel")
        )
        return
    if g["hp_ai"] <= 0:
        del duel_games[uid]
        add_stat(uid, "games")
        add_stat(uid, "wins")
        await c.message.edit_text(
            f"🏆 Победа!\n\nТы {hearts(g['hp_p'])} vs Противник {hearts(0)}", reply_markup=game_result_kb("game_duel")
        )
        return
    await c.message.edit_text(
        f"⚔️ Дуэль\n\nТы {hearts(g['hp_p'])} vs Противник {hearts(g['hp_ai'])}\n\nВыбери:", reply_markup=duel_kb()
    )


@router.callback_query(F.data == "duel_surrender")
async def cb_duel_surrender(c: CallbackQuery):
    duel_games.pop(c.from_user.id, None)
    await c.message.edit_text("🏳 Сдался.", reply_markup=game_result_kb("game_duel"))


@router.callback_query(F.data == "game_dice")
async def cb_dice(c: CallbackQuery):
    p, ai = random.randint(1, 6), random.randint(1, 6)
    if p > ai:
        res = "🏆 Победа!"
        add_stat(c.from_user.id, "wins")
    elif p < ai:
        res = "💀 Проигрыш..."
    else:
        res = "🤝 Ничья!"
    add_stat(c.from_user.id, "games")
    await c.message.edit_text(f"🎲 Ты: {p} vs Бот: {ai}\n\n{res}", reply_markup=game_result_kb("game_dice"))


@router.callback_query(F.data == "game_flip")
async def cb_flip(c: CallbackQuery):
    await c.message.edit_text(f"🪙 {random.choice(['🦅 ОРЁЛ!', '🪙 РЕШКА!'])}", reply_markup=game_result_kb("game_flip"))


@router.callback_query(F.data == "game_fco")
async def cb_fco(c: CallbackQuery):
    preds = ["🔮 Сегодня удача!", "🔮 Будь осторожен...", "🔮 Великие свершения ⚡️", "🔮 Отдохни сегодня 🌙", "🔮 Действуй сейчас!"]
    await c.message.edit_text(random.choice(preds), reply_markup=mk(row(b("🔮 Ещё", "game_fco"), b("🏠 Меню", "games_menu"))))


@router.callback_query(F.data == "game_bw")
async def cb_bw(c: CallbackQuery):
    bw_games[c.from_user.id] = [False] * 25
    await c.message.edit_text("⬛ Закрась всё поле!\n\n0/25", reply_markup=bw_kb(bw_games[c.from_user.id]))


@router.callback_query(F.data.startswith("bw_"))
async def cb_bw_move(c: CallbackQuery):
    uid = c.from_user.id
    if uid not in bw_games:
        await c.answer("Начни заново", show_alert=True)
        return
    bw_games[uid][int(c.data[3:])] = True
    filled = sum(bw_games[uid])
    if filled == 25:
        del bw_games[uid]
        add_stat(uid, "wins")
        add_stat(uid, "games")
        await c.message.edit_text("🏆 Закрасил всё!", reply_markup=game_result_kb("game_bw"))
        return
    await c.message.edit_text(f"⬛ Закрась всё поле!\n\n{filled}/25", reply_markup=bw_kb(bw_games[uid]))


@router.callback_query(F.data == "noop")
async def cb_noop(c: CallbackQuery):
    await c.answer()


@router.message(F.text.startswith("."))
async def dot_cmd(msg: Message):
    parts = msg.text.split(maxsplit=1)
    cmd = parts[0].lower()
    arg = parts[1] if len(parts) > 1 else ""
    uid = msg.from_user.id
    add_stat(uid, "commands")
    add_stat(uid, "messages")
    user_state = get_auto(uid)

    if cmd == ".help":
        await msg.answer(ALL_COMMANDS_TEXT, reply_markup=cmd_kb(), parse_mode="Markdown")
    elif cmd == ".ping":
        t = time.time()
        m = await msg.answer("⚡️...")
        await m.edit_text(f"⚡️ Понг! {int((time.time() - t) * 1000)}мс")
    elif cmd == ".spam":
        if arg:
            for _ in range(10):
                await msg.answer(arg)
        else:
            await msg.answer("❌ .spam текст")
    elif cmd == ".mute":
        user_state["mute"] = True
        await msg.answer("🔕 Авто-мут входящих сообщений активирован.")
    elif cmd == ".unmute":
        user_state["mute"] = False
        await msg.answer("🔔 Авто-мут отключен.")
    elif cmd == ".antimute":
        await msg.answer(f"⚡️ @{msg.from_user.username or msg.from_user.first_name} пробивает мьют!")
    elif cmd == ".status":
        if arg:
            user_state["status"] = arg
            await msg.answer(f"✅ Статус обновлен: {arg}")
        else:
            await msg.answer(f"📌 Текущий статус: {user_state.get('status', 'Online')}")
    elif cmd == ".nick":
        if arg:
            user_state["custom_nick"] = arg
            await msg.answer(f"✅ Кастомный ник установлен: {arg}")
        else:
            await msg.answer("❌ Использование: .nick [новое имя]")
    elif cmd == ".circle":
        await msg.answer("⭕️ Создание видеокружка (симуляция)...")
    elif cmd == ".lq":
        await msg.answer("🖼 Сжатие изображения до LQ качества...")
    elif cmd == ".story":
        await msg.answer("📱 Генерация историй...")
    elif cmd == ".bold":
        if arg:
            await msg.answer(f"<b>{arg}</b>", parse_mode="HTML")
        else:
            await msg.answer("❌ .bold текст")
    elif cmd == ".italic":
        if arg:
            await msg.answer(f"<i>{arg}</i>", parse_mode="HTML")
        else:
            await msg.answer("❌ .italic текст")
    elif cmd == ".mono":
        if arg:
            await msg.answer(f"<code>{arg}</code>", parse_mode="HTML")
        else:
            await msg.answer("❌ .mono текст")
    elif cmd == ".leet":
        if arg:
            await msg.answer(leet(arg))
        else:
            await msg.answer("❌ .leet текст")
    elif cmd == ".kawaii":
        if arg:
            await msg.answer(f"(◕‿◕✿) {arg} ✨")
        else:
            await msg.answer("❌ .kawaii текст")
    elif cmd == ".tsundere":
        if arg:
            await msg.answer(f"Б-бака! {arg}... Не думай что специально!")
        else:
            await msg.answer("❌ .tsundere текст")
    elif cmd == ".yandere":
        if arg:
            await msg.answer(f"Только для тебя 🔪 {arg} 💕")
        else:
            await msg.answer("❌ .yandere текст")
    elif cmd == ".reverse":
        if arg:
            await msg.answer(arg[::-1])
        else:
            await msg.answer("❌ .reverse текст")
    elif cmd == ".ascii":
        if arg:
            await msg.answer(f"```\n" + "\n".join(list(arg.upper())) + "\n```", parse_mode="Markdown")
        else:
            await msg.answer("❌ .ascii текст")
    elif cmd == ".sw":
        if arg:
            await msg.answer(arg.translate(sw))
        else:
            await msg.answer("❌ .sw текст")
    elif cmd == ".type":
        if arg:
            m = await msg.answer("▌")
            built = ""
            for ch in arg:
                built += ch
                try:
                    await m.edit_text(built + "▌")
                except Exception:
                    pass
                await asyncio.sleep(0.05)
            await m.edit_text(built)
        else:
            await msg.answer("❌ .type текст")
    elif cmd == ".love":
        frames = [
            "♥",
            "♥♥♥\n ♥♥♥",
            " ♥♥♥♥♥ \n♥♥♥♥♥♥♥\n  ♥♥♥♥♥",
            "♥♥♥♥♥♥\n      ♥♥♥\n             ♥",
            "♥♥♥♥♥♥♥♥♥\n  ♥♥♥♥♥♥♥\n    ♥♥♥\n     ♥",
            "💖 **Л Ю Б Л Ю** 💖\n♥♥♥♥♥♥   ♥♥♥♥♥♥\n  ♥♥♥♥♥♥♥♥♥\n    ♥♥♥♥♥\n      ♥"
        ]
        m = await msg.answer(frames[0], parse_mode="Markdown")
        for f in frames[1:]:
            await asyncio.sleep(0.35)
            try:
                await m.edit_text(f, parse_mode="Markdown")
            except Exception:
                pass
    elif cmd == ".flip":
        await msg.answer(random.choice(["🦅 ОРЁЛ!", "🪙 РЕШКА!"]))
    elif cmd == ".fco":
        await msg.answer(random.choice(["🔮 Удача сегодня!", "🔮 Осторожен...", "🔮 Действуй сейчас!", "🔮 Отдохни 🌙"]))
    elif cmd == ".dice":
        await msg.answer(f"🎲 Выпало: {random.randint(1, 6)}")
    elif cmd == ".8ball":
        if arg:
            ans = ["Да 🟢", "Нет 🔴", "Возможно 🤔", "Точно да ✨", "Ни за что 🚫", "Спроси позже ⏳", "Весьма вероятно 👍"]
            await msg.answer(f"🎱 Шар говорит: {random.choice(ans)}")
        else:
            await msg.answer("❌ Использование: .8ball [вопрос]")
    elif cmd == ".roll":
        try:
            if "d" in arg:
                count, sides = map(int, arg.split("d"))
                rolls = [random.randint(1, sides) for _ in range(min(count, 20))]
                await msg.answer(f"🎲 Бросок {arg}: {rolls} (Сумма: {sum(rolls)})")
            else:
                await msg.answer(f"🎲 Выпало: {random.randint(1, 6)}")
        except Exception:
            await msg.answer(f"🎲 Выпало: {random.randint(1, 6)}")
    elif cmd == ".quote":
        quotes = [
            "«Единственный способ делать великую работу — любить то, что вы делаете.» — Стив Джобс",
            "«Жизнь — это то, что с вами случается, пока вы строите другие планы.» — Джон Леннон",
            "«Успех — это способность идти от неудачи к неудаче без потери энтузиазма.» — Уинстон Черчилль",
            "«Лучший способ предсказать будущее — изобрести его.» — Алан Кей"
        ]
        await msg.answer(random.choice(quotes))
    elif cmd == ".compliment":
        target = msg.reply_to_message.from_user.first_name if msg.reply_to_message else "друг"
        comps = [f"@{target} — просто лучик света в этом чате! ✨", f"{target}, твоей харизме можно только позавидовать! 😎", f"{target} сегодня выглядит потрясающе! 🌟"]
        await msg.answer(random.choice(comps))
    elif cmd == ".roast":
        target = msg.reply_to_message.from_user.first_name if msg.reply_to_message else "друг"
        roasts = [f"{target}, ты бы поосторожнее с мозгами, а то вдруг поцарапаешь.", f"{target}, твой интеллект стабилен... на нуле.", f"{target} — живое доказательство того, что эволюция может делать шаги назад."]
        await msg.answer(random.choice(roasts))
    elif cmd == ".ship":
        percent = random.randint(0, 100)
        await msg.answer(f"💖 Совместимость: {percent}%\n{'❤️ Идеальная пара!' if percent > 75 else '💔 Есть над чем работать...'}")
    elif cmd == ".iq":
        iq = random.randint(40, 180)
        await msg.answer(f"🧠 Твой уровень IQ: {iq}\n{'Гений! 🔬' if iq > 140 else 'Норм пацан 👍' if iq > 90 else 'Инфузория-туфелька 🦠'}")
    elif cmd == ".encrypt":
        if arg:
            await msg.answer(f"🔒 {''.join(chr(ord(c) + 3) if c.isalpha() else c for c in arg)}")
        else:
            await msg.answer("❌ .encrypt текст")
    elif cmd == ".decrypt":
        if arg:
            await msg.answer(f"🔓 {''.join(chr(ord(c) - 3) if c.isalpha() else c for c in arg)}")
        else:
            await msg.answer("❌ .decrypt текст")
    elif cmd == ".timer":
        try:
            mins = int(arg)
            await msg.answer(f"⏱ Таймер запущен на {mins} мин.")
            async def run_timer(chat_id, minutes):
                await asyncio.sleep(minutes * 60)
                await bot.send_message(chat_id, f"⏰ Время вышло! ({minutes} мин.)")
            asyncio.create_task(run_timer(msg.chat.id, mins))
        except Exception:
            await msg.answer("❌ Использование: .timer [минуты числами]")
    elif cmd == ".poll":
        if arg:
            await bot.send_poll(chat_id=msg.chat.id, question=arg, options=["Да 👍", "Нет 👎", "Возможно 🤔"])
        else:
            await msg.answer("❌ .poll [вопрос]")
    elif cmd == ".afk":
        await msg.answer(f"💤 {msg.from_user.first_name} {arg or 'отошёл'}")
    elif cmd == ".troll":
        await msg.answer(random.choice(["😂 Серьёзно?", "🤡 Вот это поворот...", "😏 Ну-ну...", "🧐 Интересная попытка."]))
    elif cmd == ".zaebu":
        await msg.answer(f"👋 {msg.from_user.first_name} хочет поговорить!")
    elif cmd == ".info":
        u = msg.from_user
        await msg.answer(f"🪪 Карточка\n\n👤 {u.full_name}\n🆔 {u.id}\n📛 @{u.username or '—'}\n🌍 {u.language_code or '—'}")
    elif cmd == ".clone":
        if msg.reply_to_message and msg.reply_to_message.from_user:
            u = msg.reply_to_message.from_user
            await msg.answer(
                f"🪪 **Успешный клон профиля**\n\n"
                f"👤 Имя: {u.full_name}\n"
                f"🆔 ID: `{u.id}`\n"
                f"📛 Юзернейм: @{u.username or 'отсутствует'}\n"
                f"🌐 Язык: {u.language_code or '—'}",
                parse_mode="Markdown"
            )
        else:
            await msg.answer("❌ Ответь на сообщение пользователя!")
    elif cmd == ".short":
        if arg:
            w = arg.split()
            await msg.answer("📝 " + " ".join(w[:10]) + ("..." if len(w) > 10 else ""))
        else:
            await msg.answer("❌ .short текст")
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
                await msg.answer(f"🕐 Режим времени активирован для города **{city_arg.capitalize()}** [{cur_time}]", parse_mode="Markdown")
            else:
                available_cities = ", ".join([c.capitalize() for c in set(CITY_OFFSETS.keys())])
                await msg.answer(f"❌ Неизвестный город. Доступные:\n{available_cities}")
        elif sub == "off":
            user_state["time_mode"] = False
            await msg.answer("🕐 Режим времени в нике выключен.")
        else:
            city = user_state.get("city", "москва")
            offset = CITY_OFFSETS.get(city, 3)
            cur_time = (datetime.now(timezone.utc) + timedelta(hours=offset)).strftime('%H:%M')
            await msg.answer(f"🕐 Текущее время ({city.capitalize()}): [{cur_time}]")
    elif cmd == ".check":
        if msg.reply_to_message and msg.reply_to_message.document:
            d = msg.reply_to_message.document
            await msg.answer(f"📁 {d.file_name}\n📦 {d.file_size} байт")
        else:
            await msg.answer("❌ Ответь на файл")
    elif cmd == ".cat":
        await msg.answer("🐱 https://cataas.com/cat")
    elif cmd == ".nk":
        await msg.answer("🐱 няяя~ (◕‿◕✿)")
    elif cmd == ".ttt":
        ttt_games[uid] = [""] * 9
        await msg.answer("❌ Крестики-нолики\n\nТвой ход:", reply_markup=ttt_kb(ttt_games[uid]))
    elif cmd == ".rps":
        await msg.answer("✊ Выбери игру в камень-ножницы:", reply_markup=rps_kb())
    elif cmd == ".duel":
        duel_games[uid] = {"hp_p": 3, "hp_ai": 3}
        await msg.answer(f"⚔️ Дуэль\n\nТы {hearts(3)} vs Противник {hearts(3)}\n\nВыбери действие:", reply_markup=duel_kb())
    elif cmd == ".bw":
        bw_games[uid] = [False] * 25
        await msg.answer("⬛ Закрась всё поле!\n\n0/25", reply_markup=bw_kb(bw_games[uid]))
    else:
        await msg.answer(f"❓ Неизвестная команда: {cmd}")


@dp.pre_checkout_query()
async def pre_checkout(q: PreCheckoutQuery):
    await q.answer(ok=True)


@dp.message(F.successful_payment)
async def on_payment(msg: Message):
    await msg.answer(f"💙 Спасибо за {msg.successful_payment.total_amount} ⭐️!\nЭто мотивирует развивать NockMode ⚡️\n— {DEV}")


async def health(request):
    return web.Response(text="⚡️ NockMode alive")


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
