from flask import Flask, request
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    filters,
    ContextTypes,
    CommandHandler, 
    ContextTypes
)
import os
import re
import asyncio

# =========================
# TOKEN
# =========================
TOKEN = os.getenv("BOT_TOKEN")
RENDER_URL = os.getenv("RENDER_EXTERNAL_URL")

if not TOKEN:
    raise Exception("BOT_TOKEN is missing in Render environment variables")

if not RENDER_URL:
    raise Exception("RENDER_EXTERNAL_URL is missing")

print("BOT_TOKEN:", os.getenv("BOT_TOKEN"))
print("RENDER_URL:", os.getenv("RENDER_EXTERNAL_URL"))

# =========================
# RENDER WEBHOOK URL
# =========================
RENDER_URL = os.getenv("RENDER_EXTERNAL_URL")
WEBHOOK_PATH = f"/{TOKEN}"
WEBHOOK_URL = f"{RENDER_URL}{WEBHOOK_PATH}"

# =========================
# FLASK APP
# =========================
flask_app = Flask(__name__)


# 🧠 Game state (replace with Redis/DB in production)
players = {}


# ✅ Improved normalization (removes punctuation, case issues)
def normalize(text):
    return re.sub(r"[^a-z0-9 ]", "", (text or "").lower()).strip()


# 🧩 Game levels
game = [
    {
        "answer": ["let's go", "lets go"],
        "clue": (
            "Introduction\n\n"
            "Welcome! Your mission begins at Geylang Bahru.\n\n"
            "You will move through neighbourhoods that form part of our lee family and Singapore’s history, uncovering your heritage as you go.\n\n"
            "Your journey begins now. Every clue matters. Every answer unlocks the next step.\n\n"
            "🎯 Reply 'Let's go!' when you are ready to begin your adventure!"
        ),
        "success": "Cool, Let's start!\n"
    },

    {
        "answer": ["23","Twenty Three"],
        "clue": (
            "🥢 CHAPTER 1 — THE FIRST MEAL\n\n"
            "📍 Location: Geylang Bahru Hawker Centre\n\n"
            "This hawker centre was built in 1978 to serve the growing Kallang estates.\n"
            "Today, it remains a hub of old-school flavours and quiet mornings.\n\n"
            "But beneath the surface, two Michelin-recognised stalls hide in plain sight.\n\n"
            "🔎 OBJECTIVE\n"
            "Find the two Michelin stalls.\n"
            "Record their unit numbers (e.g. 01-11, 01-21).\n\n"
            "🧠 PUZZLE RULE\n"
            "Break each number into digits and add them together. (e.g. 01-11 and 01-21 = 0+1+1+1+0+1+2+1=7\n\n"
            "🎯 FINAL OUTPUT\n"
            "Submit your final sum to unlock your next message."
        ),
        "success": (
            "🍽 Enjoy your breakfast here.\n"
            "I'll give you your next location clue in the meantime.\n"
            "Set off when you are ready\n."
        )
    },

    {
        "answer": ["national aerated water company","national aerated water","aerated water"],
        "clue": (
            "🥤 CHAPTER 2 — THE LOST DRINKS\n\n"
            "📍 The Memory of Sinalco & Kickapoo\n\n"
            "Fizzy drinks from another era—bright, sweet, almost forgotten.\n"
            "Sinalco. Kickapoo Joy Juice.\n"
            "They point somewhere.\n\n"
            "A place where drinks once defined an entire industry.\n\n"
            "🔎 QUESTION\n"
            "Where do you think this place is?"
        ),
        "success": "Correct! You’ve unlocked the next location.\n"
    },

    {
        "answer": ["yellow"],
        "clue": (
            "🏭 NATIONAL AERATED WATER COMPANY\n\n"
            "A former soft drink bottling factory founded in 1929.\n"
            "It once powered Singapore’s beverage history before closing in the 1990s.\n\n"
            "🔎 QUESTION\n"
            "Inside the site, find the old refuelling pump used for delivery trucks.\n"
            "What is the colour of the pump?"
        ),
        "success": "Correct!I'll give you your next location clue\n"
    },

    {
        "answer": ["blk 102", "block 102", "102"],
        "clue": (
            "🧱 CHAPTER 3 — THE HIGH-DENSITY BLOCK\n\n"
            "“Where people heal, answers gather.”\n\n"
            "The next location is a HDB block known for its unusually high concentration of medical clinics.\n\n"
            "🔎 QUESTION\n"
            "What is the block number?"
        ),
        "success": (
            "Correct!\n\n"
            "Please head to Blk 102 Towner Road S322102.\n"
            "I'll give you your next quest.\n"
        )
    },

    {
        "answer": ["tai hin pawnshop pte ltd","tai hin","tai hin pawnshop","tai hin pawnship private limited"],
        "clue": (
            "🔎 QUEST\n"
            "Explore the block.\n\n"
            "Find the shop name that carries what falls between At and Av.\n"
        ),
        "success": (
            "Well done!\n"
            "Grab a drink as it will be a long walk to the next location.\n"
            "Next stop: Blk 75 Whampoa Drive.\n"
            "NOTE: The next quest involves guessing a unit number and it should be attempted only by the kids, with no hints from the adults!\n"
        )
    },

    {
        "answer": ["reached whampoa", "reached"],
        "clue": (
            "Let me know when you have reached the location by replying 'reached'."
        ),
        "success": ("Nice!\n"
                    "I'll give you your next quest!\n")
    },

    {
        "answer": ["07-368"],
        "clue": (
            "🧩 CHAPTER 4 — BLOCK 75 WHAMPOA DRIVE\n\n"
            "This is a place full of memories for the lee family.\n\n"
            "🔎 QUESTION\n"
            "Life comes and goes like a cycle.\n\n"
            "Within this cycle are three forms:\n"
            "a triangle, a hexagon, and an octagon.\n\n"
            "At the seventh level, the cycle reveals itself.\n\n"
            "What is the unit number? (XX-XXX)"
        ),
        "success": (
            "Take some time to explore the block if you would like.\n"
            "When ready, reply 'Ready'.\n"
        )
    },

    {
        "answer": ["ready"],
        "clue": "I'll provide the next location clue to you.\n",
        "success": ("Hope you had fun exploring!\n"
                    "I'll provide the next location clue to you.\n")
    },

    {
        "answer": ["whampoa dragon fountain","dragon","dragon fountain","whampoa dragon"],
        "clue": (
            "I am four metres tall, pointing to the sky.\n"
            "I am covered with pink, red, and jade tones.\n"
            "I guard the flats in Whampoa.\n\n"
            "🔎 QUESTION\n"
            "What am I?"
        ),
        "success": (
            "Your next destination is the Whampoa Dragon Fountain Statue, facing Blk 85 Whampoa Drive (S320085)\n"
            "Reply 'Reached' when you have arrived.\n"
        )
    },

    {
        "answer": ["reached fountain", "reached"],
        "clue": "I'll provide the next task to you.",
        "success": "Nice!\n"
    },

    {
        "answer": ["done"],
        "clue": (
            "Take a photo in front of the fountain.\n\n"
            "When you are done, reply 'Done' to continue."
        ),
        "success": "Nice!\n"
    },

    {
        "answer": ["sin hon loong bakery","sin hon loong"],
        "clue": (
            "🧩 CHAPTER 5 — THE 24 HOUR PLACE\n\n"
            "Some places never sleep. They feed the city before it wakes.\n\n"
            "🔎 QUESTION\n"
            "Open 24 hours\n"
            "Sells something eaten every morning\n"
            "Has operated for over 50 years\n\n"
            "What place is this?"
        ),
        "success": ("Correct!\n"
                    "Head over to the bakery for your next quest. The location is at 4 Whampoa Drive, S327715\n")
    },

    {
        "answer": ["reached"],
        "clue": "When you have reached, reply 'Reached'.",
        "success": "Good job!"
    },

    {
        "answer": ["1975"],
        "clue": (
            "Locate a dough refining machine used since opening.\n\n"
            "When was this machine first used?"
        ),
        "success": "Correct!\n"
    },

    {
        "answer": ["1983"],
        "clue": (
            "Find the Kodak shop near the main road.\n\n"
            "When was it opened?"
        ),
        "success": "Correct!\n"
    },
        
    {
        "answer": ["spectacles","glasses","spectacle","lens"],
        "clue": (
            "Head over to #02-01 Balestier Point, S329727\n\n"
            "This shop has a long history\n\n"
            "Tell me what does the shop sell\n\n"
        ),
        "success": ("Correct! This shop was formerly known as Lim Kay Khee Optical shop, which was located at 330 Balestier Road\n"
                    "The original Lim Kay Khee Optical Shop ceased operations in 2024, bringing to a close a business that had operated for over 78 years.\n"
                    "During those years, the Lee family were among its long-time patrons.\n")
    },

    {
        "answer": ["2","Two"],
        "clue": (
            "🧩 FINAL CHAPTER — THE MICHELIN COUNT\n\n"
            "Make your way to BLK 91 WHAMPOA MARKET.\n\n"
            "🔎 QUESTION\n"
            "How many Michelin stalls exist in this hawker centre?"
        ),
        "success": "Well done!\n"
    }
]

# =========================
# BUILD TELEGRAM APP
# =========================
application = ApplicationBuilder().token(TOKEN).build()

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = str(update.effective_user.id)
    msg = normalize(update.message.text)

    if user not in players:
        players[user] = 0
        await update.message.reply_text(game[0]["clue"])
        return

    level = players[user]

    if level >= len(game):
        await update.message.reply_text("🎉 You finished the game!")
        return

    level_data = game[level]
    answers = [normalize(a) for a in level_data["answer"]]

    if msg in answers:
        players[user] += 1
        new_level = players[user]

        if new_level < len(game):
            await update.message.reply_text(
                "✅ Correct!\n\n" +
                level_data["success"] +
                "\n\n" +
                game[new_level]["clue"]
            )
        else:
            await update.message.reply_text("🏆 Game completed! Hope you like it!")
    else:
        await update.message.reply_text("❌ Wrong answer. Try again!")

# register handler
application.add_handler(
    MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
)

# =========================
# STARTUP (set webhook)
# =========================
async def setup_webhook():
    await application.initialize()
    await application.start()
    await application.bot.set_webhook(WEBHOOK_URL)

# =========================
# FLASK WEBHOOK ROUTE
# =========================
@flask_app.post(WEBHOOK_PATH)
def webhook():
    data = request.get_json(force=True)
    update = Update.de_json(data, application.bot)

    # safe execution for Render
    import asyncio
    asyncio.run(application.process_update(update))

    return "ok", 200

async def restart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = str(update.effective_user.id)
    players[user] = 0

    await update.message.reply_text(
        "🔄 Game restarted!\n\n" + game[0]["clue"]
    )
    
application.add_handler(CommandHandler("restart", restart))

# =========================
# HEALTH CHECK
# =========================
@flask_app.get("/")
def home():
    return "Bot is running!"

# =========================
# MAIN
# =========================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))

    import threading

    def run_setup():
        import asyncio
        asyncio.run(setup_webhook())

    threading.Thread(target=run_setup).start()

    flask_app.run(host="0.0.0.0", port=port)

print("USER:", user)
print("MSG:", msg)
print("LEVEL:", level)
