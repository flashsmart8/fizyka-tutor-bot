"""
Telegram бот — Репетитор з фізики 7 клас
Підручник: Бар'яхтар, Божинова, Довгий (2024, НУШ)
"""

import os
import logging
import asyncio
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
import httpx

# ─── Config ───
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
ANTHROPIC_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# ─── Conversation memory (per user) ───
conversations: dict[int, list[dict]] = {}
MAX_HISTORY = 30  # pairs of messages to keep

# ─── Textbook structure ───
TEXTBOOK_TOC = """
ПІДРУЧНИК: Фізика 7 клас — Бар'яхтар, Божинова, Довгий (2024, НУШ)

РОЗДІЛ 1. Методи пізнання природи. Фізика як природнича наука
  §1. Фізика — наука про природу. Фізичні тіла та фізичні явища
  §2. Експериментальні та теоретичні методи досліджень законів природи
  §3. Фізичні величини та їх вимірювання
  §4. Поняття про різні види матерії. Будова речовини
  §5. Рух і взаємодія частинок речовини

РОЗДІЛ 2. Механічний рух
  Тема: Прямолінійний рівномірний рух
    §6. Механічний рух. Відносність руху та спокою
    §7. Траєкторія руху. Шлях. Переміщення
    §8. Рівномірний рух. Швидкість руху
    §9. Учимося розв'язувати задачі
    §10. Графіки рівномірного руху
    §11. Нерівномірний рух. Середня швидкість
  Тема: Рівномірний рух по колу. Коливальний рух
    §12. Рівномірний рух матеріальної точки по колу. Період обертання
    §13. Рух Землі і Місяця
    §14. Коливальний рух. Амплітуда, період і частота коливань

РОЗДІЛ 3. Взаємодія тіл. Сили в природі
  Тема: Явище інерції. Інертність та маса тіла. Густина речовини
    §15. Явище інерції
    §16. Інертність тіла. Маса
    §17. Густина. Одиниці густини
    §18. Учимося розв'язувати задачі
  Тема: Імпульс тіла. Реактивний рух
    §19. Імпульс тіла. Закон збереження імпульсу
    §20. Учимося розв'язувати задачі
    §21. Реактивний рух
  Тема: Сили в природі
    §22. Сила — міра взаємодії. Графічне зображення сил. Додавання сил
    §23. Деформація тіла. Сила пружності
    §24. Закон Гука. Динамометр
    §25. Сила тяжіння. Вага тіла
    §26. Тертя. Сила тертя
    §27. Учимося розв'язувати задачі
  Тема: Тиск твердих тіл, рідин і газів
    §28. Тиск твердих тіл на поверхню. Сила тиску
    §29. Тиск газів і рідин. Закон Паскаля
    §30. Гідростатичний тиск
    §31. Атмосферний тиск і його вимірювання. Барометри
    §32. Сполучені посудини. Манометри
    §33. Гідростатичні та пневматичні пристрої
  Тема: Виштовхувальна сила. Плавання тіл
    §34. Виштовхувальна сила в рідинах і газах. Закон Архімеда
    §35. Умови плавання тіл
    §36. Судноплавство та повітроплавання
"""

SYSTEM_PROMPT = f"""Ти — дружній та терплячий репетитор з фізики для учня 7 класу.
Тебе звати Фіза (скорочено від «фізика», як подруга-помічниця).

ПІДРУЧНИК, за яким навчається учень:
{TEXTBOOK_TOC}

ПРАВИЛА:
1. Завжди спілкуйся УКРАЇНСЬКОЮ мовою. Ніколи не переходь на російську.
2. Пояснюй простими словами, як для 13-річної дитини. Уникай складних наукових термінів — а якщо треба використати термін, одразу поясни його простою мовою.
3. Використовуй приклади з реального життя: спорт, їжа, телефони, автобуси, велосипеди, ігри — те, що цікаво підліткам.
4. Коли пояснюєш формулу — покажи її, поясни кожну букву, і одразу розв'яжи простий приклад з числами.
5. Якщо учень каже "не розумію" — поясни інакше, іншими словами та іншим прикладом. Ніколи не повторюй те саме.
6. Коли учень ПИТАЄ про теорію (наприклад "що таке інерція?", "як працює тиск?", "поясни закон Архімеда") — ОДРАЗУ давай зрозуміле пояснення з прикладом. Ніколи не кажи "здогадайся" чи "подумай сам" на теоретичні питання.
7. Коли учень надсилає ЗАДАЧУ З ЧИСЛАМИ для розв'язання — тоді веди крок за кроком, але з підказками: "Дивись, нам відомо X і Y. Яку формулу ми вчили для цього? Підказка: вона пов'язує швидкість і час..." Якщо учень не може відповісти — дай відповідь сам і поясни.
8. Хвали за правильні кроки: "Точно! 💪", "Молодець, правильно міркуєш! 🎯"
9. Використовуй емодзі помірно — вони роблять спілкування живішим.
10. Якщо учень питає щось не з фізики — м'яко поверни до теми: "Цікаве питання! Але давай повернемося до фізики 😊"
11. Відповідай коротко і по суті. Не пиши стіни тексту — краще 3-5 речень за раз. Якщо тема велика — розбий на частини і питай "Продовжимо? 👇"
12. Коли учень вперше пише або обирає тему — дай ДУЖЕ коротке пояснення (3-4 речення), потім спитай чи зрозуміло.
13. ГОЛОВНЕ: ти помічниця, яка ДОПОМАГАЄ зрозуміти. Завжди давай корисну відповідь. Ніколи не залишай учня без пояснення.

МЕНЮ ТЕМ:
Коли учень натискає "📚 Обрати тему" або подібне — покажи список розділів і запропонуй обрати.
Коли учень натискає "❓ Задати питання" — скажи: "Питай що завгодно з фізики 7 класу! 🔬"
Коли учень натискає "📝 Розв'язати задачу" — скажи: "Надішли умову задачі, і ми розберемо її крок за кроком! ✏️"
Коли учень натискає "🔄 Нова тема" — запропонуй обрати нову тему з підручника.
"""

# ─── Menu keyboard ───
def main_menu_keyboard():
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("📚 Обрати тему"), KeyboardButton("❓ Задати питання")],
            [KeyboardButton("📝 Розв'язати задачу"), KeyboardButton("🔄 Нова тема")],
        ],
        resize_keyboard=True,
    )

def topics_keyboard():
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("1️⃣ Методи пізнання природи")],
            [KeyboardButton("2️⃣ Механічний рух")],
            [KeyboardButton("3️⃣ Інерція, маса, густина")],
            [KeyboardButton("4️⃣ Імпульс і реактивний рух")],
            [KeyboardButton("5️⃣ Сили в природі")],
            [KeyboardButton("6️⃣ Тиск твердих тіл, рідин і газів")],
            [KeyboardButton("7️⃣ Закон Архімеда. Плавання тіл")],
            [KeyboardButton("🔙 Назад")],
        ],
        resize_keyboard=True,
    )


# ─── Anthropic API call ───
async def ask_claude(user_id: int, user_message: str) -> str:
    """Send message to Claude API with conversation history."""
    if user_id not in conversations:
        conversations[user_id] = []

    history = conversations[user_id]
    history.append({"role": "user", "content": user_message})

    # Trim history
    if len(history) > MAX_HISTORY * 2:
        history[:] = history[-(MAX_HISTORY * 2):]

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": ANTHROPIC_API_KEY,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": ANTHROPIC_MODEL,
                    "max_tokens": 1024,
                    "system": SYSTEM_PROMPT,
                    "messages": history,
                },
            )
            resp.raise_for_status()
            data = resp.json()

        assistant_text = data["content"][0]["text"]
        history.append({"role": "assistant", "content": assistant_text})
        return assistant_text

    except httpx.HTTPStatusError as e:
        logger.error(f"Anthropic API error: {e.response.status_code} — {e.response.text}")
        history.pop()  # remove failed user msg
        return "Вибач, сталась технічна помилка 😔 Спробуй ще раз через хвилинку."
    except Exception as e:
        logger.error(f"Anthropic error: {e}", exc_info=True)
        history.pop()
        return "Вибач, щось пішло не так 😔 Спробуй ще раз."


# ─── Handlers ───
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    conversations.pop(user_id, None)  # fresh start

    await update.message.reply_text(
        f"Привіт, {user.first_name}! 👋\n\n"
        "Я — *Фіза* 🧑‍🔬, твоя помічниця з фізики для 7 класу.\n\n"
        "Я допоможу тобі:\n"
        "📚 Зрозуміти будь-яку тему з підручника\n"
        "❓ Відповісти на питання\n"
        "📝 Розв'язати задачі крок за кроком\n\n"
        "Обирай що потрібно 👇",
        parse_mode="Markdown",
        reply_markup=main_menu_keyboard(),
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = (update.message.text or "").strip()

    if not text:
        return

    # ── Menu buttons ──
    if text == "📚 Обрати тему" or text == "🔄 Нова тема":
        conversations.pop(user_id, None)
        await update.message.reply_text(
            "Обери розділ підручника 👇",
            reply_markup=topics_keyboard(),
        )
        return

    if text == "🔙 Назад":
        await update.message.reply_text(
            "Повертаємось до головного меню 👇",
            reply_markup=main_menu_keyboard(),
        )
        return

    if text == "❓ Задати питання":
        await update.message.reply_text(
            "Питай що завгодно з фізики 7 класу! 🔬\n"
            "Наприклад: «Що таке інерція?» або «Чому кораблі не тонуть?»",
            reply_markup=main_menu_keyboard(),
        )
        return

    if text == "📝 Розв'язати задачу":
        await update.message.reply_text(
            "Надішли умову задачі, і ми розберемо її крок за кроком! ✏️\n"
            "Можеш написати текстом або надіслати фото задачі з підручника.",
            reply_markup=main_menu_keyboard(),
        )
        return

    # ── Topic buttons → feed as context to Claude ──
    topic_map = {
        "1️⃣ Методи пізнання природи": "Розкажи коротко про Розділ 1: Методи пізнання природи (§1-§5). Що таке фізика, фізичні тіла, будова речовини. Дай дуже коротке пояснення і спитай з чого почати.",
        "2️⃣ Механічний рух": "Розкажи коротко про Розділ 2: Механічний рух (§6-§14). Рівномірний рух, швидкість, графіки, рух по колу, коливання. Дай дуже коротке пояснення і спитай з чого почати.",
        "3️⃣ Інерція, маса, густина": "Розкажи коротко про тему: Явище інерції, маса, густина (§15-§18). Дай дуже коротке пояснення і спитай з чого почати.",
        "4️⃣ Імпульс і реактивний рух": "Розкажи коротко про тему: Імпульс тіла, закон збереження імпульсу, реактивний рух (§19-§21). Дай дуже коротке пояснення і спитай з чого почати.",
        "5️⃣ Сили в природі": "Розкажи коротко про тему: Сили в природі (§22-§27). Сила, деформація, закон Гука, сила тяжіння, вага, тертя. Дай дуже коротке пояснення і спитай з чого почати.",
        "6️⃣ Тиск твердих тіл, рідин і газів": "Розкажи коротко про тему: Тиск (§28-§33). Тиск твердих тіл, закон Паскаля, гідростатичний тиск, атмосферний тиск, сполучені посудини. Дай дуже коротке пояснення і спитай з чого почати.",
        "7️⃣ Закон Архімеда. Плавання тіл": "Розкажи коротко про тему: Виштовхувальна сила, закон Архімеда, плавання тіл, судноплавство (§34-§36). Дай дуже коротке пояснення і спитай з чого почати.",
    }

    if text in topic_map:
        conversations.pop(user_id, None)  # fresh context for new topic
        text = topic_map[text]

    # ── Send to Claude ──
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    response = await ask_claude(user_id, text)

    # Telegram messages max 4096 chars — split if needed
    if len(response) <= 4096:
        await update.message.reply_text(
            response,
            parse_mode="Markdown",
            reply_markup=main_menu_keyboard(),
        )
    else:
        # Split into chunks
        for i in range(0, len(response), 4096):
            chunk = response[i : i + 4096]
            await update.message.reply_text(chunk, parse_mode="Markdown")
            await asyncio.sleep(0.3)


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle photos — student might send a photo of a problem from the textbook."""
    await update.message.reply_text(
        "Бачу фото! 📷\n\n"
        "На жаль, поки що я не вмію читати зображення. "
        "Будь ласка, *напиши текстом* умову задачі або питання, "
        "і я обов'язково допоможу! ✏️",
        parse_mode="Markdown",
        reply_markup=main_menu_keyboard(),
    )


async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conversations.pop(update.effective_user.id, None)
    await update.message.reply_text(
        "Розмову очищено! Починаємо з чистого аркуша 📄",
        reply_markup=main_menu_keyboard(),
    )


# ─── Main ───
def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("clear", clear))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    logger.info("🧑‍🔬 Physics tutor bot started!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
