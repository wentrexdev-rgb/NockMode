import asyncio
import os
import random
import time
from datetime import datetime, timezone, timedelta
from typing import Optional

from aiohttp import web
from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.types import (
    Message,
    CallbackQuery,
    PreCheckoutQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

TOKEN = "1780243280:044LckyLaJ8_K0STT0sd4ouvETONgRYUSPP"
API_BASE = os.getenv("TELEGRAM_API_BASE", "http://31.77.9.111:8081")
PORT = int(os.getenv("PORT", "8080"))
DEV = os.getenv("DEV_USERNAME", "@dick")

if not TOKEN:
    raise RuntimeError("BOT_TOKEN не установлен")

session = AiohttpSession(
    api=TelegramAPIServer.from_base(API_BASE)
)

bot = Bot(
    token=TOKEN,
    session=session
)

dp = Dispatcher()
router = Router()
dp.include_router(router)

user_stats: dict[int, dict[str, int]] = {}
auto_states: dict[int, dict] = {}


CITY_OFFSETS = {
    "москва": 3,
    "moscow": 3,
    "спб": 3,
    "питер": 3,
    "санкт-петербург": 3,
    "екатеринбург": 5,
    "екб": 5,
    "ekaterinburg": 5,
    "новосибирск": 7,
    "novosibirsk": 7,
    "калининград": 2,
    "kaliningrad": 2,
    "самара": 4,
    "samara": 4,
    "омск": 6,
    "omsk": 6,
    "красноярск": 7,
    "krasnoyarsk": 7,
    "иркутск": 8,
    "irkutsk": 8,
    "якутск": 9,
    "yakutsk": 9,
    "владивосток": 10,
    "vladivostok": 10,
    "минск": 3,
    "minsk": 3,
    "киев": 2,
    "kiev": 2,
}


LEET_TABLE = {
    "a": "4",
    "e": "3",
    "i": "1",
    "o": "0",
    "s": "5",
    "t": "7",
    "l": "|",
    "g": "9",
    "b": "8",
}


SWITCH_TABLE = str.maketrans({
    "q": "й",
    "w": "ц",
    "e": "у",
    "r": "к",
    "t": "е",
    "y": "н",
    "u": "г",
    "i": "ш",
    "o": "щ",
    "p": "з",
    "a": "ф",
    "s": "ы",
    "d": "в",
    "f": "а",
    "g": "п",
    "h": "р",
    "j": "о",
    "k": "л",
    "l": "д",
    "z": "я",
    "x": "ч",
    "c": "с",
    "v": "м",
    "b": "и",
    "n": "т",
    "m": "ь",
    "Q": "Й",
    "W": "Ц",
    "E": "У",
    "R": "К",
    "T": "Е",
    "Y": "Н",
    "U": "Г",
    "I": "Ш",
    "O": "Щ",
    "P": "З",
    "A": "Ф",
    "S": "Ы",
    "D": "В",
    "F": "А",
    "G": "П",
    "H": "Р",
    "J": "О",
    "K": "Л",
    "L": "Д",
    "Z": "Я",
    "X": "Ч",
    "C": "С",
    "V": "М",
    "B": "И",
    "N": "Т",
    "M": "Ь",
})


def get_auto(uid: int) -> dict:
    return auto_states.setdefault(
        uid,
        {
            "format": False,
            "troll": False,
            "afk": False,
            "mute": False,
            "antimute": False,
            "nick": False,
            "time_mode": False,
            "reply": False,
            "city": "москва",
            "status": "Online",
            "custom_nick": "",
            "afk_text": "",
        },
    )


def get_stats(uid: int) -> dict[str, int]:
    return user_stats.setdefault(
        uid,
        {
            "commands": 0,
            "games": 0,
            "wins": 0,
            "messages": 0,
        },
    )


def add_stat(uid: int, key: str) -> None:
    stats = get_stats(uid)
    stats[key] = stats.get(key, 0) + 1


def leet(text: str) -> str:
    return "".join(
        LEET_TABLE.get(char.lower(), char)
        for char in text
    )


def main_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📊 Статистика",
                    callback_data="menu:stats",
                ),
                InlineKeyboardButton(
                    text="🤡 Команды",
                    callback_data="menu:help",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="⚙️ Настройки",
                    callback_data="menu:settings",
                ),
                InlineKeyboardButton(
                    text="🎲 Кубик",
                    callback_data="menu:dice",
                ),
            ],
        ]
    )


def back_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⬅️ Назад",
                    callback_data="menu:main",
                )
            ]
        ]
    )


def welcome(name: str) -> str:
    return (
        "╔══════════════════════════════╗\n"
        "        🤡 ClownMode Bot\n"
        "╚══════════════════════════════╝\n\n"
        f"Привет, {name}! 👋\n\n"
        "Бот для команд, развлечений и автоматизации.\n"
        "Используй кнопки ниже или команды через точку.\n\n"
        "Напиши .help, чтобы посмотреть все команды."
    )


ALL_COMMANDS_TEXT = (
    "🤡 ClownMode — список команд\n\n"

    "🔒 Модерация\n"
    "├ .spam [текст]\n"
    "├ .mute\n"
    "├ .unmute\n"
    "├ .antimute [on/off]\n"
    "└ .afk [текст]\n\n"

    "🪄 Текст\n"
    "├ .bold [текст]\n"
    "├ .italic [текст]\n"
    "├ .mono [текст]\n"
    "├ .leet [текст]\n"
    "├ .kawaii [текст]\n"
    "├ .tsundere [текст]\n"
    "├ .yandere [текст]\n"
    "├ .reverse [текст]\n"
    "├ .ascii [текст]\n"
    "├ .qr [текст]\n"
    "├ .sw [текст]\n"
    "└ .type [текст]\n\n"

    "🎮 Игры\n"
    "├ .love\n"
    "├ .slot\n"
    "├ .dice\n"
    "├ .flip\n"
    "├ .rps [rock/scissors/paper]\n"
    "├ .8ball [вопрос]\n"
    "├ .roll [NdN]\n"
    "└ .iq\n\n"

    "👤 Профиль\n"
    "├ .status [текст]\n"
    "├ .nick [текст]\n"
    "├ .time [on/off город]\n"
    "├ .ping\n"
    "├ .info\n"
    "└ .stats\n\n"

    "🧰 Дополнительно\n"
    "├ .timer [минуты]\n"
    "├ .poll [вопрос]\n"
    "├ .quote\n"
    "├ .ship\n"
    "├ .cat\n"
    "└ .nk"
)


async def safe_delete_business_message(
    business_connection_id: str,
    message_id: int,
) -> bool:
    try:
        await bot.delete_business_messages(
            business_connection_id=business_connection_id,
            message_ids=[message_id],
        )
        return True
    except Exception:
        try:
            await bot.delete_business_message(
                business_connection_id=business_connection_id,
                message_id=message_id,
            )
            return True
        except Exception:
            return False


async def send_business_message(
    msg: Message,
    text: str,
    business_connection_id: str,
    **kwargs,
):
    return await bot.send_message(
        chat_id=msg.chat.id,
        text=text,
        business_connection_id=business_connection_id,
        **kwargs,
    )


async def send_response(
    msg: Message,
    text: str,
    is_business: bool,
    business_connection_id: Optional[str] = None,
    **kwargs,
):
    if is_business and business_connection_id:
        return await send_business_message(
            msg,
            text,
            business_connection_id,
            **kwargs,
        )

    return await msg.answer(
        text,
        **kwargs,
    )


def parse_command(text: str):
    if not text:
        return None, ""

    text = text.strip()

    if not text:
        return None, ""

    if not text.startswith(".") and not text.startswith("/"):
        return None, ""

    parts = text.split(maxsplit=1)

    command = parts[0].lower()

    if command.startswith("/"):
        command = command.split("@", 1)[0]

    argument = parts[1].strip() if len(parts) > 1 else ""

    return command, argument


async def execute_command(
    msg: Message,
    text: str,
    uid: int,
    is_business: bool = False,
    business_connection_id: Optional[str] = None,
):
    command, arg = parse_command(text)

    if not command:
        return False

    add_stat(uid, "commands")
    add_stat(uid, "messages")

    state = get_auto(uid)

    async def reply(content: str, **kwargs):
        return await send_response(
            msg,
            content,
            is_business,
            business_connection_id,
            **kwargs,
        )

    if command in {"/help", ".help", ".команды"}:
        await reply(
            ALL_COMMANDS_TEXT,
            reply_markup=main_menu_keyboard(),
        )
        return True

    if command in {"/start", ".start"}:
        await reply(
            welcome(msg.from_user.first_name),
            reply_markup=main_menu_keyboard(),
        )
        return True

    if command == ".ping":
        started = time.perf_counter()

        sent = await reply("🤡 Проверяю...")

        elapsed = round(
            (time.perf_counter() - started) * 1000
        )

        try:
            await sent.edit_text(
                f"🤡 Понг!\n\n⏱ {elapsed} мс"
            )
        except Exception:
            pass

        return True

    if command == ".spam":
        if not arg:
            await reply("❌ Использование: .spam [текст]")
            return True

        for _ in range(10):
            await reply(arg)

        return True

    if command == ".mute":
        state["mute"] = True

        await reply(
            "🔕 Авто-мут включён.\n"
            "Входящие сообщения собеседника будут удаляться, "
            "если Telegram разрешает удаление для этой Business-связи."
        )

        return True

    if command == ".unmute":
        state["mute"] = False
        await reply("🔔 Авто-мут выключен.")
        return True

    if command == ".antimute":
        value = arg.lower()

        if value == "off":
            state["antimute"] = False
            await reply("🔴 Авто-подпись выключена.")
        else:
            state["antimute"] = True
            await reply("🟢 Авто-подпись включена.")

        return True

    if command == ".afk":
        state["afk"] = True
        state["afk_text"] = arg or "отошёл"

        await reply(
            f"💤 AFK включён: {state['afk_text']}"
        )

        return True

    if command == ".status":
        if not arg:
            await reply(
                f"📌 Текущий статус: {state['status']}"
            )
            return True

        state["status"] = arg

        await reply(
            f"✅ Статус обновлён:\n{arg}"
        )

        return True

    if command == ".nick":
        if not arg:
            await reply("❌ Использование: .nick [новый ник]")
            return True

        state["custom_nick"] = arg

        await reply(
            f"✅ Кастомный ник установлен:\n{arg}"
        )

        return True

    if command == ".bold":
        if not arg:
            await reply("❌ Использование: .bold [текст]")
            return True

        safe = (
            arg.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )

        await reply(
            f"<b>{safe}</b>",
            parse_mode="HTML",
        )

        return True

    if command == ".italic":
        if not arg:
            await reply("❌ Использование: .italic [текст]")
            return True

        safe = (
            arg.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )

        await reply(
            f"<i>{safe}</i>",
            parse_mode="HTML",
        )

        return True

    if command == ".mono":
        if not arg:
            await reply("❌ Использование: .mono [текст]")
            return True

        safe = (
            arg.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )

        await reply(
            f"<code>{safe}</code>",
            parse_mode="HTML",
        )

        return True

    if command == ".leet":
        if not arg:
            await reply("❌ Использование: .leet [текст]")
            return True

        await reply(leet(arg))
        return True

    if command == ".kawaii":
        if not arg:
            await reply("❌ Использование: .kawaii [текст]")
            return True

        await reply(f"(◕‿◕✿) {arg} ✨")
        return True

    if command == ".tsundere":
        if not arg:
            await reply("❌ Использование: .tsundere [текст]")
            return True

        await reply(
            f"Б-бака! {arg}... Не думай, что я специально!"
        )

        return True

    if command == ".yandere":
        if not arg:
            await reply("❌ Использование: .yandere [текст]")
            return True

        await reply(
            f"Только для тебя 💕 {arg}"
        )

        return True

    if command == ".reverse":
        if not arg:
            await reply("❌ Использование: .reverse [текст]")
            return True

        await reply(arg[::-1])
        return True

    if command == ".ascii":
        if not arg:
            await reply("❌ Использование: .ascii [текст]")
            return True

        result = "\n".join(
            list(arg.upper())
        )

        await reply(
            f"```\n{result}\n```",
            parse_mode="Markdown",
        )

        return True

    if command == ".qr":
        if not arg:
            await reply(
                "❌ Использование: .qr [текст или ссылка]"
            )
            return True

        from urllib.parse import quote

        encoded = quote(arg, safe="")

        url = (
            "https://api.qrserver.com/v1/create-qr-code/"
            f"?size=250x250&data={encoded}"
        )

        if is_business and business_connection_id:
            await bot.send_photo(
                chat_id=msg.chat.id,
                photo=url,
                caption=f"📱 QR-код\n{arg}",
                business_connection_id=business_connection_id,
            )
        else:
            await msg.answer_photo(
                photo=url,
                caption=f"📱 QR-код\n{arg}",
            )

        return True

    if command == ".sw":
        if not arg:
            await reply("❌ Использование: .sw [текст]")
            return True

        await reply(
            arg.translate(SWITCH_TABLE)
        )

        return True

    if command == ".type":
        if not arg:
            await reply("❌ Использование: .type [текст]")
            return True

        sent = await reply("▌")
        current = ""

        for char in arg:
            current += char

            try:
                await sent.edit_text(
                    current + "▌"
                )
            except Exception:
                pass

            await asyncio.sleep(0.05)

        try:
            await sent.edit_text(current)
        except Exception:
            pass

        return True

    if command == ".love":
        frames = [
            "♥",
            "♥♥♥\n ♥♥♥",
            " ♥♥♥♥♥ \n♥♥♥♥♥♥♥\n  ♥♥♥♥♥",
            "♥♥♥♥♥♥\n      ♥♥♥\n             ♥",
            "♥♥♥♥♥♥♥♥♥\n  ♥♥♥♥♥♥♥\n    ♥♥♥\n     ♥",
            "💖 Л Ю Б Л Ю 💖\n"
            "♥♥♥♥♥♥   ♥♥♥♥♥♥\n"
            "  ♥♥♥♥♥♥♥♥♥\n"
            "    ♥♥♥♥♥\n"
            "      ♥",
        ]

        sent = await reply(frames[0])

        for frame in frames[1:]:
            await asyncio.sleep(0.35)

            try:
                await sent.edit_text(frame)
            except Exception:
                pass

        return True

    if command == ".flip":
        await reply(
            random.choice([
                "🦅 ОРЁЛ!",
                "🪙 РЕШКА!",
            ])
        )

        return True

    if command == ".slot":
        add_stat(uid, "games")

        if is_business and business_connection_id:
            await bot.send_dice(
                chat_id=msg.chat.id,
                emoji="🎰",
                business_connection_id=business_connection_id,
            )
        else:
            await msg.answer_dice(
                emoji="🎰"
            )

        return True

    if command == ".dice":
        add_stat(uid, "games")

        if is_business and business_connection_id:
            await bot.send_dice(
                chat_id=msg.chat.id,
                emoji="🎲",
                business_connection_id=business_connection_id,
            )
        else:
            await msg.answer_dice(
                emoji="🎲"
            )

        return True

    if command == ".8ball":
        if not arg:
            await reply(
                "❌ Использование: .8ball [вопрос]"
            )
            return True

        answers = [
            "Да 🟢",
            "Нет 🔴",
            "Возможно 🤔",
            "Точно да ✨",
            "Ни за что 🚫",
            "Спроси позже ⏳",
            "Весьма вероятно 👍",
        ]

        await reply(
            f"🎱 Шар говорит: {random.choice(answers)}"
        )

        return True

    if command == ".roll":
        if not arg:
            await reply(
                f"🎲 Выпало: {random.randint(1, 6)}"
            )
            return True

        try:
            dice = arg.lower()

            if "d" not in dice:
                raise ValueError

            count_text, sides_text = dice.split("d", 1)

            count = int(count_text)
            sides = int(sides_text)

            if count < 1 or sides < 2:
                raise ValueError

            count = min(count, 20)
            sides = min(sides, 100000)

            rolls = [
                random.randint(1, sides)
                for _ in range(count)
            ]

            await reply(
                f"🎲 {count}d{sides}\n\n"
                f"Выпало: {rolls}\n"
                f"Сумма: {sum(rolls)}"
            )

        except Exception:
            await reply(
                "❌ Формат: .roll NdN\n"
                "Например: .roll 2d20"
            )

        return True

    if command == ".rps":
        choice = arg.lower().strip()

        mapping = {
            "камень": "rock",
            "ножницы": "scissors",
            "бумага": "paper",
        }

        choice = mapping.get(choice, choice)

        if choice not in {
            "rock",
            "scissors",
            "paper",
        }:
            await reply(
                "❌ Использование:\n"
                ".rps rock\n"
                ".rps scissors\n"
                ".rps paper"
            )
            return True

        ai = random.choice([
            "rock",
            "scissors",
            "paper",
        ])

        labels = {
            "rock": "✊",
            "scissors": "✌️",
            "paper": "🖐",
        }

        wins_against = {
            "rock": "scissors",
            "scissors": "paper",
            "paper": "rock",
        }

        add_stat(uid, "games")

        if choice == ai:
            result = "🤝 Ничья!"
        elif wins_against[choice] == ai:
            result = "🏆 Победа!"
            add_stat(uid, "wins")
        else:
            result = "💀 Проигрыш..."

        await reply(
            f"Ты {labels[choice]} vs Бот {labels[ai]}\n\n"
            f"{result}"
        )

        return True

    if command == ".quote":
        quotes = [
            "«Единственный способ делать великую работу — любить то, что вы делаете.»",
            "«Жизнь — это то, что с вами случается, пока вы строите другие планы.»",
            "«Успех — это способность идти от неудачи к неудаче без потери энтузиазма.»",
            "«Лучший способ предсказать будущее — изобрести его.»",
        ]

        await reply(
            random.choice(quotes)
        )

        return True

    if command == ".ship":
        percent = random.randint(0, 100)

        await reply(
            f"💖 Совместимость: {percent}%"
        )

        return True

    if command == ".iq":
        iq = random.randint(40, 180)

        if iq > 140:
            text = "Гений! 🔬"
        elif iq > 90:
            text = "Норм 👍"
        else:
            text = "Сегодня не твой день 🦠"

        await reply(
            f"🧠 Тестовый IQ: {iq}\n{text}"
        )

        return True

    if command == ".timer":
        try:
            minutes = int(arg)

            if minutes <= 0 or minutes > 10080:
                raise ValueError

        except ValueError:
            await reply(
                "❌ Использование: .timer [минуты]\n"
                "Допустимо от 1 до 10080."
            )
            return True

        await reply(
            f"⏱ Таймер запущен на {minutes} мин."
        )

        async def timer_task(
            chat_id: int,
            duration: int,
            business_id: Optional[str],
        ):
            await asyncio.sleep(duration * 60)

            try:
                if business_id:
                    await bot.send_message(
                        chat_id=chat_id,
                        text=f"⏰ Время вышло! ({duration} мин.)",
                        business_connection_id=business_id,
                    )
                else:
                    await bot.send_message(
                        chat_id=chat_id,
                        text=f"⏰ Время вышло! ({duration} мин.)",
                    )
            except Exception as exc:
                print(
                    f"Timer error: {exc}"
                )

        asyncio.create_task(
            timer_task(
                msg.chat.id,
                minutes,
                business_connection_id
                if is_business
                else None,
            )
        )

        return True

    if command == ".poll":
        if not arg:
            await reply(
                "❌ Использование: .poll [вопрос]"
            )
            return True

        options = [
            "Да 👍",
            "Нет 👎",
            "Возможно 🤔",
        ]

        if is_business and business_connection_id:
            await bot.send_poll(
                chat_id=msg.chat.id,
                question=arg,
                options=options,
                business_connection_id=business_connection_id,
            )
        else:
            await msg.answer_poll(
                question=arg,
                options=options,
            )

        return True

    if command == ".info":
        user = msg.from_user

        await reply(
            "🪪 Информация\n\n"
            f"👤 {user.full_name}\n"
            f"🆔 {user.id}\n"
            f"📛 @{user.username or '—'}\n"
            f"🌍 {user.language_code or '—'}"
        )

        return True

    if command == ".stats":
        stats = get_stats(uid)

        await reply(
            "📊 Твоя статистика\n\n"
            f"🤡 Команд: {stats['commands']}\n"
            f"🎮 Игр: {stats['games']}\n"
            f"🏆 Побед: {stats['wins']}\n"
            f"💬 Сообщений: {stats['messages']}"
        )

        return True

    if command == ".time":
        parts = arg.split(maxsplit=1)

        subcommand = (
            parts[0].lower()
            if parts
            else ""
        )

        city_arg = (
            parts[1].strip().lower()
            if len(parts) > 1
            else "москва"
        )

        if subcommand == "on":
            if city_arg not in CITY_OFFSETS:
                await reply(
                    "❌ Неизвестный город.\n\n"
                    "Примеры: Москва, Минск, "
                    "Екатеринбург, Новосибирск."
                )
                return True

            state["city"] = city_arg
            state["time_mode"] = True

            offset = CITY_OFFSETS[city_arg]

            current = (
                datetime.now(timezone.utc)
                + timedelta(hours=offset)
            ).strftime("%H:%M")

            await reply(
                f"🕐 Режим времени включён\n"
                f"Город: {city_arg.capitalize()}\n"
                f"Время: {current}"
            )

            return True

        if subcommand == "off":
            state["time_mode"] = False
            await reply("🕐 Режим времени выключен.")
            return True

        city = state.get(
            "city",
            "москва",
        )

        offset = CITY_OFFSETS.get(
            city,
            3,
        )

        current = (
            datetime.now(timezone.utc)
            + timedelta(hours=offset)
        ).strftime("%H:%M")

        await reply(
            f"🕐 Текущее время\n"
            f"Город: {city.capitalize()}\n"
            f"Время: {current}"
        )

        return True

    if command == ".cat":
        await reply(
            "🐱 https://cataas.com/cat"
        )
        return True

    if command == ".nk":
        await reply(
            "🐱 няяя~ (◕‿◕✿)"
        )
        return True

    await reply(
        f"❓ Неизвестная команда: {command}\n\n"
        "Используй .help для списка команд."
    )

    return True


@router.business_message()
async def business_message_handler(msg: Message):
    if not msg.business_connection_id:
        return

    uid = (
        msg.from_user.id
        if msg.from_user
        else 0
    )

    state = get_auto(uid)

    if not msg.outgoing:
        if state.get("mute", False):
            await safe_delete_business_message(
                msg.business_connection_id,
                msg.message_id,
            )

        return

    if not msg.text:
        return

    command, _ = parse_command(msg.text)

    if not command:
        return

    await safe_delete_business_message(
        msg.business_connection_id,
        msg.message_id,
    )

    try:
        await execute_command(
            msg=msg,
            text=msg.text,
            uid=uid,
            is_business=True,
            business_connection_id=msg.business_connection_id,
        )

    except TelegramForbiddenError:
        print("Telegram запретил действие с Business-сообщением.")

    except TelegramBadRequest as exc:
        print(
            f"Telegram BadRequest: {exc}"
        )

    except Exception as exc:
        print(
            f"Business command error: {exc}"
        )


@router.message(F.text.startswith("."))
async def regular_dot_command(msg: Message):
    if not msg.from_user:
        return

    uid = msg.from_user.id

    try:
        await execute_command(
            msg=msg,
            text=msg.text,
            uid=uid,
            is_business=False,
        )

    except Exception as exc:
        print(
            f"Regular command error: {exc}"
        )


@router.message(F.text.startswith("/"))
async def regular_slash_command(msg: Message):
    if not msg.from_user:
        return

    uid = msg.from_user.id

    command, _ = parse_command(msg.text)

    if command not in {
        "/start",
        "/help",
    }:
        return

    try:
        await execute_command(
            msg=msg,
            text=msg.text,
            uid=uid,
            is_business=False,
        )

    except Exception as exc:
        print(
            f"Slash command error: {exc}"
        )


@router.callback_query(F.data == "menu:main")
async def callback_main(
    callback: CallbackQuery,
):
    await callback.answer()

    try:
        await callback.message.edit_text(
            welcome(
                callback.from_user.first_name
            ),
            reply_markup=main_menu_keyboard(),
        )
    except Exception:
        await callback.message.answer(
            welcome(
                callback.from_user.first_name
            ),
            reply_markup=main_menu_keyboard(),
        )


@router.callback_query(F.data == "menu:help")
async def callback_help(
    callback: CallbackQuery,
):
    await callback.answer()

    try:
        await callback.message.edit_text(
            ALL_COMMANDS_TEXT,
            reply_markup=back_keyboard(),
        )
    except Exception:
        await callback.message.answer(
            ALL_COMMANDS_TEXT,
            reply_markup=back_keyboard(),
        )


@router.callback_query(F.data == "menu:stats")
async def callback_stats(
    callback: CallbackQuery,
):
    await callback.answer()

    stats = get_stats(
        callback.from_user.id
    )

    text = (
        "📊 Твоя статистика\n\n"
        f"🤡 Команд: {stats['commands']}\n"
        f"🎮 Игр: {stats['games']}\n"
        f"🏆 Побед: {stats['wins']}\n"
        f"💬 Сообщений: {stats['messages']}"
    )

    try:
        await callback.message.edit_text(
            text,
            reply_markup=back_keyboard(),
        )
    except Exception:
        await callback.message.answer(
            text,
            reply_markup=back_keyboard(),
        )


@router.callback_query(F.data == "menu:settings")
async def callback_settings(
    callback: CallbackQuery,
):
    await callback.answer()

    state = get_auto(
        callback.from_user.id
    )

    text = (
        "⚙️ Настройки\n\n"
        f"🔕 Авто-мут: "
        f"{'Включён' if state['mute'] else 'Выключен'}\n"
        f"🟢 Авто-подпись: "
        f"{'Включена' if state['antimute'] else 'Выключена'}\n"
        f"💤 AFK: "
        f"{'Включён' if state['afk'] else 'Выключен'}\n"
        f"📌 Статус: {state['status']}\n"
        f"🌍 Город: {state['city'].capitalize()}"
    )

    try:
        await callback.message.edit_text(
            text,
            reply_markup=back_keyboard(),
        )
    except Exception:
        await callback.message.answer(
            text,
            reply_markup=back_keyboard(),
        )


@router.callback_query(F.data == "menu:dice")
async def callback_dice(
    callback: CallbackQuery,
):
    await callback.answer()

    await callback.message.answer_dice(
        emoji="🎲"
    )


@router.pre_checkout_query()
async def pre_checkout(
    query: PreCheckoutQuery,
):
    await query.answer(
        ok=True
    )


@router.message(F.successful_payment)
async def successful_payment(
    msg: Message,
):
    payment = msg.successful_payment

    await msg.answer(
        f"💙 Спасибо за {payment.total_amount} ⭐️!\n"
        f"Это мотивирует развивать ClownMode 🤡\n"
        f"— {DEV}"
    )


async def health(
    request: web.Request,
):
    return web.json_response(
        {
            "status": "ok",
            "service": "ClownMode",
        }
    )


async def start_http_server():
    app = web.Application()

    app.router.add_get(
        "/",
        health,
    )

    runner = web.AppRunner(app)

    await runner.setup()

    site = web.TCPSite(
        runner,
        "0.0.0.0",
        PORT,
    )

    await site.start()

    return runner


async def main():
    runner = await start_http_server()

    try:
        await bot.delete_webhook(
            drop_pending_updates=True
        )

        print(
            f"ClownMode started on port {PORT}"
        )

        await dp.start_polling(
            bot,
            allowed_updates=dp.resolve_used_update_types(),
        )

    finally:
        await runner.cleanup()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
