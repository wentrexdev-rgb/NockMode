import asyncio, random, time, logging
from datetime import datetime
from aiohttp import web
from aiogram import Bot, Dispatcher, F, Router
from aiogram.types import (
    Message, CallbackQuery, LabeledPrice, PreCheckoutQuery,
    InlineKeyboardMarkup, InlineKeyboardButton as Btn
)

TOKEN = "8673189276:AAF34u6ioYEO8FJodFhS-bDnCkU5SGdp42U"
CHANNEL = "@nockart"
DEV = "@nockdevs"
ONLINE_CHAT = "@push_frog"

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher()
router = Router()
dp.include_router(router)

ttt_games, rps_games, duel_games, bw_games = {}, {}, {}, {}
auto_states, user_stats, notif_states, online_active = {}, {}, {}, {}

def get_auto(uid):
    return auto_states.get(uid, {
        "format": False, "troll": False, "afk": False,
        "mute": False, "nick": False, "time_mode": False,
        "reply": False, "antimute_ping": False,
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

async def check_sub(uid):
    try:
        m = await bot.get_chat_member(CHANNEL, uid)
        return m.status not in ("left", "kicked")
    except:
        return False

def mk(*rows): return InlineKeyboardMarkup(inline_keyboard=list(rows))
def row(*btns): return list(btns)
def b(text, cb=None, url=None): return Btn(text=text, callback_data=cb, url=url)
def back(to="main"): return mk(row(b("← Назад", to)))

def main_menu():
    return mk(
        row(b("📋 Команды", "cmd_menu"), b("🤖 Авто-режимы", "auto_menu")),
        row(b("🎮 Игры", "games_menu"), b("⚙️ Настройки", "settings_menu")),
        row(b("📊 Статистика", "stats"), b("ℹ️ О боте", "about")),
        row(b("📖 Туториал", "tutorial"), b("💙 Поддержать", "donate")),
    )

def sub_check_kb():
    return mk(
        row(b("📢 Подписаться на @nockart", url="https://t.me/nockart")),
        row(b("✅ Я подписался — проверить", "check_sub")),
    )

def cmd_kb():
    return mk(
        row(b("🔒 Модерация", "cmd_mod"), b("🪄 Текст", "cmd_text")),
        row(b("🔥 Фан", "cmd_fun"), b("🎮 Игры", "cmd_games")),
        row(b("🪪 Инфо", "cmd_info"), b("👤 Профиль", "cmd_profile")),
        row(b("🎨 Медиа", "cmd_media"), b("⚡️ Система", "cmd_system")),
        row(b("← Назад", "main")),
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
        rows.append([Btn(text=s[board[i*3+j]], callback_data="noop" if board[i*3+j] else f"ttt_{i*3+j}") for j in range(3)])
    rows.append([b("🏳 Сдаться", "ttt_surrender")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def game_result_kb(replay, menu="games_menu"):
    return mk(row(b("🔄 Реванш", replay), b("🏠 Меню", menu)))

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
        rows.append([Btn(text="⬛" if board[i*5+j] else "⬜", callback_data="noop" if board[i*5+j] else f"bw_{i*5+j}") for j in range(5)])
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
    def t(key, label): return b(f"{'🟢' if s.get(key) else '🔴'} {label}", f"auto_{key}")
    return mk(
        row(t("format", "Авто-формат текста")),
        row(t("troll", "Авто-тролль")),
        row(t("afk", "AFK режим")),
        row(t("mute", "Авто-мут входящих")),
        row(t("nick", "Авто-имя (ник)")),
        row(t("time_mode", "Время в фамилии")),
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

def welcome(name):
    return (
        "╔══════════════════════════════╗\n"
        "        ⚡️ NockMode Bot        \n"
        "╚══════════════════════════════╝\n\n"
        f"Привет, {name}! 👋\n\n"
        "Бизнес-бот нового поколения.\n"
        "Работает прямо в твоих чатах\n"
        "через Telegram Business.\n\n"
        "● Команды через точку — мгновенно\n"
        "● Игры прямо в кнопках — с AI\n"
        "● Авто-режимы — включай одной кнопкой\n"
        "● Полностью локально — без внешних API"
    )

def hearts(n): return "❤️" * n + "🖤" * (3 - n)

def check_ttt(b_):
    for a,bc,c_ in [(0,1,2),(3,4,5),(6,7,8),(0,3,6),(1,4,7),(2,5,8),(0,4,8),(2,4,6)]:
        if b_[a] and b_[a] == b_[bc] == b_[c_]: return b_[a]

def leet(t):
    return "".join({"a":"4","e":"3","i":"1","o":"0","s":"5","t":"7","l":"|","g":"9","b":"8"}.get(c.lower(),c) for c in t)

sw = str.maketrans(
    "qwertyuiop[]asdfghjkl;'zxcvbnm,./QWERTYUIOP{}ASDFGHJKL:\"ZXCVBNM<>?",
    "йцукенгшщзхъфывапролджэячсмитьбюЙЦУКЕНГШЩЗХЪФЫВАПРОЛДЖЭЯЧСМИТЬБЮ"
)

@router.message(F.text.in_({"/start", "/help"}))
async def cmd_start(msg: Message):
    if not await check_sub(msg.from_user.id):
        await msg.answer("⚡️ NockMode Bot\n\nДля использования необходимо\nподписаться на канал автора 👇", reply_markup=sub_check_kb())
        return
    await msg.answer(welcome(msg.from_user.first_name), reply_markup=main_menu())

@router.callback_query(F.data == "check_sub")
async def cb_check_sub(c: CallbackQuery):
    if await check_sub(c.from_user.id):
        await c.message.edit_text(welcome(c.from_user.first_name), reply_markup=main_menu())
    else:
        await c.answer("❌ Ты ещё не подписан!", show_alert=True)

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
        "1️⃣ Открой Telegram → Настройки\n"
        "   → Telegram Business\n\n"
        "2️⃣ Найди раздел «Чат-боты»\n"
        "   и нажми «Добавить бота»\n\n"
        "3️⃣ Найди @NockModeBot и добавь\n\n"
        "4️⃣ Разреши боту:\n"
        "   ● Читать сообщения\n"
        "   ● Отвечать за тебя\n"
        "   ● Доступ к профилю\n\n"
        "5️⃣ Готово! Пиши команды с точкой\n"
        "   прямо в любом чате ⚡️\n\n"
        "По вопросам: @nockdevs"
    )
    await c.message.edit_text(text, reply_markup=back("main"))

@router.callback_query(F.data == "about")
async def cb_about(c: CallbackQuery):
    text = "ℹ️ NockMode Bot\n\nВерсия: 1.0.0\nРазработчик: @nockdevs\nКанал: @nockart\n\nБот создан для Telegram Business.\nЛёгкий, быстрый, без лишних зависимостей.\n\n⚡️ NockMode — быстрее. Чище. Лучше."
    kb = mk(row(b("📢 Канал", url="https://t.me/nockart"), b("👤 Разработчик", url="https://t.me/nockdevs")), row(b("← Назад", "main")))
    await c.message.edit_text(text, reply_markup=kb)

@router.callback_query(F.data == "donate")
async def cb_donate(c: CallbackQuery):
    await c.message.edit_text("💙 Поддержать разработку\n\nЕсли NockMode помогает тебе —\nподдержи автора! Это мотивирует\nвыпускать обновления быстрее 🚀\n\nВыбери сумму:", reply_markup=donate_kb())

@router.callback_query(F.data.startswith("donate_"))
async def cb_donate_pay(c: CallbackQuery):
    stars = int(c.data.split("_")[1])
    await c.bot.send_invoice(chat_id=c.from_user.id, title="💙 Поддержка NockMode",
        description=f"Спасибо за поддержку! ({stars} ⭐️)", payload=f"donate_{stars}",
        currency="XTR", prices=[LabeledPrice(label=f"⭐️ {stars} звёзд", amount=stars)])
    await c.answer()

@router.callback_query(F.data == "stats")
async def cb_stats(c: CallbackQuery):
    s = get_stats(c.from_user.id)
    text = f"📊 Твоя статистика\n\n⚡️ Команд: {s['commands']}\n🎮 Игр: {s['games']}\n🏆 Побед: {s['wins']}\n💬 Сообщений: {s['messages']}"
    await c.message.edit_text(text, reply_markup=mk(row(b("🔄 Обновить", "stats"), b("← Назад", "main"))))

@router.callback_query(F.data == "auto_menu")
async def cb_auto_menu(c: CallbackQuery):
    await c.message.edit_text("🤖 Авто-режимы\n\nНажми чтобы включить / выключить:", reply_markup=auto_kb(c.from_user.id))

@router.callback_query(F.data.startswith("auto_"))
async def cb_auto(c: CallbackQuery):
    key = c.data[5:]
    toggle_auto(c.from_user.id, key)
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
    active = online_active[uid]
    await c.message.edit_reply_markup(reply_markup=settings_kb(uid))
    if active:
        await c.answer("🟢 Вечный онлайн включён!", show_alert=True)
        asyncio.create_task(online_loop(uid))
    else:
        await c.answer("🔴 Вечный онлайн выключен", show_alert=True)

async def online_loop(uid):
    while online_active.get(uid, False):
        try:
            msg = await bot.send_message(ONLINE_CHAT, "⚡️")
            await asyncio.sleep(1)
            await bot.delete_message(ONLINE_CHAT, msg.message_id)
        except Exception as e:
            print(f"online error: {e}")
        await asyncio.sleep(15)

@router.callback_query(F.data == "clear_cache")
async def cb_clear_cache(c: CallbackQuery):
    uid = c.from_user.id
    for d in [ttt_games, rps_games, duel_games, bw_games]: d.pop(uid, None)
    await c.answer("🗑 Кэш очищен!", show_alert=True)

@router.callback_query(F.data == "cmd_mod")
async def cb_cmd_mod(c: CallbackQuery):
    text = ("🔒 Модерация\n\n"
        "├ .spam [текст] — повторит 10 раз\n"
        "├ .mute — авто-удаление входящих\n"
        "├ .unmute — вернуть сообщения\n"
        "├ .nomute — обход мута чужих ботов\n"
        "├ .antimute — пробить мьют собеседника\n"
        "├ .afk [текст] — автоответ «отошёл»\n"
        "├ .sw [текст] — смена раскладки\n"
        "├ .type [текст] — печать по буквам\n"
        "├ .zaebu — позвать в диалог\n"
        "├ .a_mute — мут всего входящего\n"
        "├ .a_troll — подколы на каждое сообщение\n"
        "└ .troll — ядовитый подкол")
    kb = mk(row(b("🔇 Как работает .antimute?", "antimute_info")), row(b("← Назад", "cmd_menu")))
    await c.message.edit_text(text, reply_markup=kb)

@router.callback_query(F.data == "antimute_info")
async def cb_antimute_info(c: CallbackQuery):
    text = ("⚡️ .antimute — как это работает\n\n"
        "Юзерботы ставят мьют локально на своём устройстве.\n\n"
        "Что делает .antimute:\n\n"
        "▸ Отправляет @упоминание — пробивает большинство фильтров\n\n"
        "▸ Серия невидимых символов сбивает авто-фильтры\n\n"
        "▸ Голосовое сообщение проходит отдельным каналом\n\n"
        "Эффективность: ~70% ✅")
    kb = mk(row(b("⚡️ Запустить .antimute", "run_antimute")), row(b("← Назад", "cmd_mod")))
    await c.message.edit_text(text, reply_markup=kb)

@router.callback_query(F.data == "run_antimute")
async def cb_run_antimute(c: CallbackQuery):
    await c.answer("⚡️ Отправь .antimute в нужном чате!", show_alert=True)

@router.callback_query(F.data == "cmd_text")
async def cb_cmd_text(c: CallbackQuery):
    text = ("🪄 Текст и стиль\n\n"
        "├ .bold [текст] — жирный\n"
        "├ .italic [текст] — курсив\n"
        "├ .mono [текст] — моноширинный\n"
        "├ .leet [текст] — l33t стиль\n"
        "├ .kawaii [текст] — (◕‿◕✿) стиль\n"
        "├ .tsundere [текст] — цундере стиль\n"
        "└ .yandere [текст] — яндере стиль")
    await c.message.edit_text(text, reply_markup=back("cmd_menu"))

@router.callback_query(F.data == "cmd_fun")
async def cb_cmd_fun(c: CallbackQuery):
    text = "🔥 Спам и Фан\n\n├ .love — анимация сердечка ❤️\n├ .flip — монетка 🪙\n├ .fco — предсказание 🔮\n└ .cat — кот 🐱"
    await c.message.edit_text(text, reply_markup=back("cmd_menu"))

@router.callback_query(F.data == "cmd_games")
async def cb_cmd_games(c: CallbackQuery):
    text = "🎮 Игры\n\n├ .ttt — крестики-нолики\n├ .rps — камень-ножницы\n├ .duel — дуэль\n├ .dice — кубик\n├ .flip — монетка\n└ .bw — закрась поле"
    await c.message.edit_text(text, reply_markup=back("cmd_menu"))

@router.callback_query(F.data == "cmd_info")
async def cb_cmd_info(c: CallbackQuery):
    text = "🪪 Информация\n\n├ .info — карточка пользователя\n├ .clone — клон профиля\n├ .dox — открытая информация\n├ .short [текст] — пересказ\n└ .gifts — подарки аккаунта 🎁"
    await c.message.edit_text(text, reply_markup=back("cmd_menu"))

@router.callback_query(F.data == "cmd_profile")
async def cb_cmd_profile(c: CallbackQuery):
    text = "👤 Профиль\n\n├ .status [текст] — статус в имени\n├ .nick [текст] — автообновление имени\n├ .time — время в фамилии\n└ .ping — задержка бота ⚡️"
    await c.message.edit_text(text, reply_markup=back("cmd_menu"))

@router.callback_query(F.data == "cmd_media")
async def cb_cmd_media(c: CallbackQuery):
    text = "🎨 Медиа\n\n├ .gif — анимация из медиа\n├ .circle — видеокружок\n├ .lq — сжать фото\n├ .fv — голосовое громче\n├ .story — 9 историй\n├ .publ — одна история\n└ .nk — неко-тян 🐱"
    await c.message.edit_text(text, reply_markup=back("cmd_menu"))

@router.callback_query(F.data == "cmd_system")
async def cb_cmd_system(c: CallbackQuery):
    text = "⚡️ Система\n\n├ .ping — задержка бота\n├ .check — информация о файле\n└ .save — скачать видео по ссылке"
    await c.message.edit_text(text, reply_markup=back("cmd_menu"))

@router.callback_query(F.data == "game_ttt")
async def cb_ttt_start(c: CallbackQuery):
    ttt_games[c.from_user.id] = [""] * 9
    await c.message.edit_text("❌ Крестики-нолики\n\nТвой ход — нажми на клетку:", reply_markup=ttt_kb(ttt_games[c.from_user.id]))

@router.callback_query(F.data.startswith("ttt_"))
async def cb_ttt(c: CallbackQuery):
    uid = c.from_user.id
    if uid not in ttt_games: await c.answer("Начни заново", show_alert=True); return
    idx = int(c.data[4:])
    board = ttt_games[uid]
    board[idx] = "X"
    w = check_ttt(board)
    if w:
        del ttt_games[uid]; add_stat(uid, "wins"); add_stat(uid, "games")
        return await c.message.edit_text("🏆 Ты победил!", reply_markup=game_result_kb("game_ttt"))
    if "" not in board:
        del ttt_games[uid]; add_stat(uid, "games")
        return await c.message.edit_text("🤝 Ничья!", reply_markup=game_result_kb("game_ttt"))
    empty = [i for i, v in enumerate(board) if not v]
    board[random.choice(empty)] = "O"
    w = check_ttt(board)
    if w:
        del ttt_games[uid]; add_stat(uid, "games")
        return await c.message.edit_text("💀 Ты проиграл...", reply_markup=game_result_kb("game_ttt"))
    if "" not in board:
        del ttt_games[uid]; add_stat(uid, "games")
        return await c.message.edit_text("🤝 Ничья!", reply_markup=game_result_kb("game_ttt"))
    await c.message.edit_text("❌ Твой ход:", reply_markup=ttt_kb(board))

@router.callback_query(F.data == "ttt_surrender")
async def cb_ttt_surrender(c: CallbackQuery):
    ttt_games.pop(c.from_user.id, None)
    await c.message.edit_text("🏳 Сдался.", reply_markup=game_result_kb("game_ttt"))

@router.callback_query(F.data == "game_rps")
async def cb_rps(c: CallbackQuery):
    await c.message.edit_text("✊ Камень-ножницы-бумага\n\nВыбери:", reply_markup=rps_kb())

@router.callback_query(F.data.startswith("rps_"))
async def cb_rps_move(c: CallbackQuery):
    uid = c.from_user.id
    choice = c.data[4:]
    ai = random.choice(["rock", "scissors", "paper"])
    labels = {"rock": "✊", "scissors": "✌️", "paper": "🖐"}
    wins = {"rock": "scissors", "scissors": "paper", "paper": "rock"}
    res = "🤝 Ничья!" if choice == ai else ("🏆 Победа!" if wins[choice] == ai else "💀 Проигрыш...")
    if wins.get(choice) == ai: add_stat(uid, "wins")
    add_stat(uid, "games")
    await c.message.edit_text(f"Ты {labels[choice]} vs Бот {labels[ai]}\n\n{res}", reply_markup=game_result_kb("game_rps"))

@router.callback_query(F.data == "game_duel")
async def cb_duel(c: CallbackQuery):
    duel_games[c.from_user.id] = {"hp_p": 3, "hp_ai": 3}
    await c.message.edit_text(f"⚔️ Дуэль\n\nТы {hearts(3)} vs Противник {hearts(3)}\n\nВыбери действие:", reply_markup=duel_kb())

@router.callback_query(F.data.startswith("duel_") & ~F.data.in_({"duel_accept","duel_decline"}))
async def cb_duel_action(c: CallbackQuery):
    uid = c.from_user.id
    if uid not in duel_games: await c.answer("Начни заново", show_alert=True); return
    g = duel_games[uid]
    action = c.data[5:]
    ai = random.choice(["hit","block","dodge","crit"])
    dp_, dai = 0, 0
    if action == "hit":
        if ai not in ("block","dodge"): dai = 1
        if ai == "hit": dp_ = 1
    elif action == "crit":
        if ai not in ("block","dodge"): dai = 2
        else: dp_ = 1
    elif action == "dodge":
        if ai not in ("hit","crit"): dp_ = 1
    if ai == "hit" and action not in ("block","dodge"): dp_ = max(dp_,1)
    if ai == "crit" and action not in ("block","dodge"): dp_ = max(dp_,2)
    g["hp_p"] = max(0, g["hp_p"] - dp_)
    g["hp_ai"] = max(0, g["hp_ai"] - dai)
    if g["hp_p"] <= 0:
        del duel_games[uid]; add_stat(uid, "games")
        return await c.message.edit_text(f"💀 Проигрыш!\n\nТы {hearts(0)} vs Противник {hearts(g['hp_ai'])}", reply_markup=game_result_kb("game_duel"))
    if g["hp_ai"] <= 0:
        del duel_games[uid]; add_stat(uid, "games"); add_stat(uid, "wins")
        return await c.message.edit_text(f"🏆 Победа!\n\nТы {hearts(g['hp_p'])} vs Противник {hearts(0)}", reply_markup=game_result_kb("game_duel"))
    await c.message.edit_text(f"⚔️ Дуэль\n\nТы {hearts(g['hp_p'])} vs Противник {hearts(g['hp_ai'])}\n\nВыбери действие:", reply_markup=duel_kb())

@router.callback_query(F.data == "duel_surrender")
async def cb_duel_surrender(c: CallbackQuery):
    duel_games.pop(c.from_user.id, None)
    await c.message.edit_text("🏳 Сдался в дуэли.", reply_markup=game_result_kb("game_duel"))

@router.callback_query(F.data == "game_dice")
async def cb_dice(c: CallbackQuery):
    p, ai = random.randint(1,6), random.randint(1,6)
    res = "🏆 Победа!" if p > ai else ("💀 Проигрыш..." if p < ai else "🤝 Ничья!")
    add_stat(c.from_user.id, "games")
    if p > ai: add_stat(c.from_user.id, "wins")
    await c.message.edit_text(f"🎲 Ты: {p} vs Бот: {ai}\n\n{res}", reply_markup=game_result_kb("game_dice"))

@router.callback_query(F.data == "game_flip")
async def cb_flip(c: CallbackQuery):
    await c.message.edit_text(f"🪙 {random.choice(['🦅 ОРЁЛ!', '🪙 РЕШКА!'])}", reply_markup=game_result_kb("game_flip"))

@router.callback_query(F.data == "game_fco")
async def cb_fco(c: CallbackQuery):
    preds = ["🔮 Сегодня тебя ждёт удача!","🔮 Будь осторожен...","🔮 Великие свершения ждут ⚡️","🔮 Звёзды говорят: отдохни 🌙","🔮 Неожиданная встреча изменит день","🔮 Действуй сейчас!","🔮 Дважды подумай..."]
    await c.message.edit_text(random.choice(preds), reply_markup=mk(row(b("🔮 Ещё", "game_fco"), b("🏠 Меню", "games_menu"))))

@router.callback_query(F.data == "game_bw")
async def cb_bw(c: CallbackQuery):
    bw_games[c.from_user.id] = [False]*25
    await c.message.edit_text("⬛ Закрась всё поле!\n\nЗакрашено: 0/25", reply_markup=bw_kb(bw_games[c.from_user.id]))

@router.callback_query(F.data.startswith("bw_"))
async def cb_bw_move(c: CallbackQuery):
    uid = c.from_user.id
    if uid not in bw_games: await c.answer("Начни заново", show_alert=True); return
    bw_games[uid][int(c.data[3:])] = True
    filled = sum(bw_games[uid])
    if filled == 25:
        del bw_games[uid]; add_stat(uid, "wins"); add_stat(uid, "games")
        return await c.message.edit_text("🏆 Ты закрасил всё поле!", reply_markup=game_result_kb("game_bw"))
    await c.message.edit_text(f"⬛ Закрась всё поле!\n\nЗакрашено: {filled}/25", reply_markup=bw_kb(bw_games[uid]))

@router.callback_query(F.data == "noop")
async def cb_noop(c: CallbackQuery): await c.answer()

@router.business_message(F.text.startswith("."))
async def dot_cmd(msg: Message):
    parts = msg.text.split(maxsplit=1)
    cmd = parts[0].lower()
    arg = parts[1] if len(parts) > 1 else ""
    uid = msg.from_user.id
    add_stat(uid, "commands"); add_stat(uid, "messages")

    if cmd == ".ping":
        t = time.time(); m = await msg.answer("⚡️...")
        await m.edit_text(f"⚡️ Понг! {int((time.time()-t)*1000)}мс")
    elif cmd == ".spam":
        [await msg.answer(arg) for _ in range(10)] if arg else await msg.answer("❌ .spam текст")
    elif cmd == ".bold":
        await msg.answer(f"<b>{arg}</b>", parse_mode="HTML") if arg else await msg.answer("❌ .bold текст")
    elif cmd == ".italic":
        await msg.answer(f"<i>{arg}</i>", parse_mode="HTML") if arg else await msg.answer("❌ .italic текст")
    elif cmd == ".mono":
        await msg.answer(f"<code>{arg}</code>", parse_mode="HTML") if arg else await msg.answer("❌ .mono текст")
    elif cmd == ".leet":
        await msg.answer(leet(arg)) if arg else await msg.answer("❌ .leet текст")
    elif cmd == ".kawaii":
        await msg.answer(f"(◕‿◕✿) {arg} ✨") if arg else await msg.answer("❌ .kawaii текст")
    elif cmd == ".tsundere":
        await msg.answer(f"Б-бака! {arg}... Не думай что я специально!") if arg else await msg.answer("❌ .tsundere текст")
    elif cmd == ".yandere":
        await msg.answer(f"Только для тебя... 🔪 {arg} 💕") if arg else await msg.answer("❌ .yandere текст")
    elif cmd == ".sw":
        await msg.answer(arg.translate(sw)) if arg else await msg.answer("❌ .sw текст")
    elif cmd == ".type":
        if arg:
            m = await msg.answer("▌"); built = ""
            for ch in arg:
                built += ch
                try: await m.edit_text(built + "▌")
                except: pass
            await m.edit_text(built)
        else: await msg.answer("❌ .type текст")
    elif cmd == ".love":
        frames = ["❤️","💕","💗","💓","💞","💖","✨💖✨"]
        m = await msg.answer(frames[0])
        for f in frames[1:]:
            await asyncio.sleep(0.4)
            try: await m.edit_text(f)
            except: pass
    elif cmd == ".flip":
        await msg.answer(random.choice(["🦅 ОРЁЛ!", "🪙 РЕШКА!"]))
    elif cmd == ".fco":
        await msg.answer(random.choice(["🔮 Сегодня удача!","🔮 Будь осторожен...","🔮 Великие свершения ⚡️","🔮 Отдохни сегодня 🌙"]))
    elif cmd == ".dice":
        await msg.answer(f"🎲 Выпало: {random.randint(1,6)}")
    elif cmd == ".afk":
        await msg.answer(f"💤 {msg.from_user.first_name} сейчас {arg or 'отошёл'}")
    elif cmd == ".troll":
        await msg.answer(random.choice(["😂 Серьёзно?","🤡 Вот это поворот...","😏 Ну-ну...","🧐 Интересная попытка."]))
    elif cmd == ".zaebu":
        await msg.answer(f"👋 {msg.from_user.first_name} хочет поговорить!")
    elif cmd == ".antimute":
        await msg.answer(f"⚡️ @{msg.from_user.username or msg.from_user.first_name} пытается достучаться!")
    elif cmd == ".info":
        u = msg.from_user
        await msg.answer(f"🪪 Карточка\n\n👤 {u.full_name}\n🆔 {u.id}\n📛 @{u.username or '—'}\n🌍 {u.language_code or '—'}")
    elif cmd == ".clone":
        if msg.reply_to_message:
            u = msg.reply_to_message.from_user
            await msg.answer(f"🪪 Клон\n\n👤 {u.full_name}\n🆔 {u.id}\n📛 @{u.username or '—'}")
        else: await msg.answer("❌ Ответь на сообщение")
    elif cmd == ".short":
        if arg:
            w = arg.split(); await msg.answer("📝 " + " ".join(w[:10]) + ("..." if len(w)>10 else ""))
        else: await msg.answer("❌ .short текст")
    elif cmd == ".ping":
        await msg.answer(f"⚡️ Понг!")
    elif cmd == ".time":
        await msg.answer(f"🕐 {datetime.now().strftime('%H:%M')}")
    elif cmd == ".check":
        if msg.reply_to_message and msg.reply_to_message.document:
            d = msg.reply_to_message.document
            await msg.answer(f"📁 {d.file_name}\n📦 {d.file_size} байт")
        else: await msg.answer("❌ Ответь на файл")
    elif cmd == ".cat":
        await msg.answer("🐱 https://cataas.com/cat")
    elif cmd == ".nk":
        await msg.answer("🐱 няяя~ (◕‿◕✿)")
    else:
        await msg.answer(f"❓ Неизвестная команда: {cmd}\nНапиши /help")

@dp.pre_checkout_query()
async def pre_checkout(q: PreCheckoutQuery): await q.answer(ok=True)

@dp.message(lambda m: m.successful_payment is not None)
async def on_payment(msg: Message):
    await msg.answer(f"💙 Спасибо за {msg.successful_payment.total_amount} ⭐️!\nЭто мотивирует развивать NockMode ⚡️\n— @nockdevs")

async def health(request): return web.Response(text="⚡️ NockMode alive")

async def main():
    app = web.Application()
    app.router.add_get("/", health)
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", 8080).start()
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
