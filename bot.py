import os
import time
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes,
    ConversationHandler, CallbackQueryHandler, filters
)
from openai import OpenAI
from openai.assistants import AssistantRunnable, ThreadStore
from openai.types.beta.threads import MessageContentText

load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)

LANGUAGE, TOPIC, CLIENT_INPUT = range(3)

ASSISTANT_MAP = {
    "Стоимость услуг агентства": "asst_iv3ToS7Gf0fAI30c1kVu592C",
    "Бюджет мероприятия": "asst_AuriGhAoIQ4CsJKt2E4Sw9cB",
    "Сроки подготовки": "asst_uWLM6ShrMJ8DCEm1XvKgPMmy"
}

user_last_topic = {}
LOG_FILE = "bot_dialog_log.txt"

def log_message(user_id, role, content):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"{user_id} | {role.upper()} | {content}\n")

LANGUAGE_OPTIONS = {"Русский": "ru", "English": "en"}
language_markup = InlineKeyboardMarkup(
    [[InlineKeyboardButton(text, callback_data=code)] for text, code in LANGUAGE_OPTIONS.items()]
)

topic_keyboard_ru = [
    [InlineKeyboardButton("Стоимость услуг агентства", callback_data="Стоимость услуг агентства")],
    [InlineKeyboardButton("Бюджет мероприятия", callback_data="Бюджет мероприятия")],
    [InlineKeyboardButton("Сроки подготовки", callback_data="Сроки подготовки")]
]
topic_markup_ru = InlineKeyboardMarkup(topic_keyboard_ru)

topic_keyboard_en = [
    [InlineKeyboardButton("Pricing Objections", callback_data="Стоимость услуг агентства")],
    [InlineKeyboardButton("Event Budget", callback_data="Бюджет мероприятия")],
    [InlineKeyboardButton("Timeline & Deadlines", callback_data="Сроки подготовки")]
]
topic_markup_en = InlineKeyboardMarkup(topic_keyboard_en)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Выберите язык / Choose your language:", reply_markup=language_markup)
    return LANGUAGE

async def select_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        await query.answer()
    except:
        pass
    lang = query.data
    context.user_data["lang"] = lang
    markup = topic_markup_ru if lang == "ru" else topic_markup_en
    prompt = "Выберите тему возражений:" if lang == "ru" else "Choose a topic:"
    await query.edit_message_text(prompt, reply_markup=markup)
    return TOPIC

async def select_topic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        await query.answer()
    except:
        pass
    topic = query.data
    context.user_data["topic"] = topic
    context.user_data["assistant_id"] = ASSISTANT_MAP[topic]
    user_last_topic[update.effective_user.id] = topic
    prompt = "Введите позицию и аргументы клиента:" if context.user_data["lang"] == "ru" else "Please enter the client's position and arguments:"
    await query.edit_message_text(prompt)
    return CLIENT_INPUT

async def handle_client_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_text = update.message.text
    lang = context.user_data.get("lang", "en")
    assistant_id = context.user_data.get("assistant_id")
    if not assistant_id:
        topic = user_last_topic.get(user_id)
        assistant_id = ASSISTANT_MAP.get(topic)
        context.user_data["assistant_id"] = assistant_id

    user_input = f"Ответь по-русски. Вот запрос клиента:\n{user_text}" if lang == "ru" else user_text

    thread_store = ThreadStore(client=client)
    thread = thread_store.get(user_id=str(user_id)) or thread_store.create(user_id=str(user_id))
    assistant = AssistantRunnable(client=client, assistant_id=assistant_id)

    response = assistant.run(thread=thread, input=user_input)

    for message in response.output.messages:
        if isinstance(message.content[0], MessageContentText):
            reply = message.content[0].text.value
            log_message(user_id, "user", user_input)
            log_message(user_id, "assistant", reply)
            await update.message.reply_text(reply)
            break
    return ConversationHandler.END

async def continue_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    topic = user_last_topic.get(user_id)
    if topic:
        context.user_data["assistant_id"] = ASSISTANT_MAP[topic]
        context.user_data["topic"] = topic
        await update.message.reply_text("Продолжим разговор. Введите новую реплику клиента:")
        return CLIENT_INPUT
    else:
        await update.message.reply_text("Вы ещё не начинали диалог. Используйте /start.")
        return ConversationHandler.END

async def reset_memory(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    thread_store = ThreadStore(client=client)
    thread_store.delete(user_id=str(user_id))
    user_last_topic.pop(user_id, None)
    await update.message.reply_text("Память очищена. Начните заново с помощью /start.")

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Диалог завершен.")
    return ConversationHandler.END

def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            CommandHandler("continue", continue_conversation),
            CommandHandler("reset", reset_memory)
        ],
        states={
            LANGUAGE: [CallbackQueryHandler(select_language)],
            TOPIC: [CallbackQueryHandler(select_topic)],
            CLIENT_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_client_input)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        per_message=True
    )
    app.add_handler(conv_handler)
    print("Бот запущен...")
    app.run_polling()

if __name__ == "__main__":
    main()