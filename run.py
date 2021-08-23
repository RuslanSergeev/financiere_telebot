import json
import logging
import time
import pytz
import datetime
from telegram import Update

from telegram.ext import (
    Updater, 
    CommandHandler, 
    MessageHandler, 
    Filters, 
    CallbackContext
)
from authentication import TelegramAuth
from busines_logic import Logic

auth = TelegramAuth('telegram.json')
logic = Logic(
    'grossbook.csv',
    'telegram.json',
    'budget.json',
    'rub')

notify_time = datetime.time(
    hour=10, minute=0, second=0,
    tzinfo=pytz.timezone(auth.config['timezone'])
)

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

def buy_message(update: Update, context: CallbackContext) -> None:
    if auth.ok(update):
        buy_reply =  logic.buy(update)
        noreply = update.message.reply_text(
            buy_reply
        )
        time.sleep(10)
        noreply.delete()

def dayly_job(context: CallbackContext) -> None:
    print('in the dayly job...')
    dayly_job_ok = logic.dayly_job()
    if dayly_job_ok:
        for chat in context.job.context:
            context.bot.send_photo(
                chat_id=chat,
                photo = open('payments.png', 'rb')
            )

def expenses_command(update: Update, context: CallbackContext) -> None:
    if auth.ok(update):
        expenses_reply = logic.get_expenses(update)
        noreply = update.message.reply_text(
            expenses_reply
        )
        time.sleep(10)
        noreply.delete()
        update.message.delete()

def month_command(update: Update, context: CallbackContext) -> None:
    if auth.ok(update):
        month_stats_reply = logic.get_month_stats(update)
        noreply = update.message.reply_text(
            month_stats_reply
        )
        time.sleep(10)
        noreply.delete()
        update.message.delete()

def day_command(update: Update, context: CallbackContext) -> None:
    if auth.ok(update):
        day_stats_ok = logic.get_day_stats(update)
        if day_stats_ok:
            context.bot.send_photo(
                chat_id=update.message.chat_id,
                photo = open('daystats.png', 'rb')
            )
        update.message.delete()

def pocket_command(update: Update, context: CallbackContext) -> None:
    if auth.ok(update):
        pocket_stats_ok = logic.get_pocket_summary(update, 'eur')
        if pocket_stats_ok:
            noreply = context.bot.send_photo(
                chat_id=update.message.chat_id,
                photo = open('pocket_summary.png', 'rb')
            )
        time.sleep(10)
        noreply.delete()
        update.message.delete()

def target_command(update: Update, context: CallbackContext) -> None:
    f''' Will show how big the debt is: 
        All the salary except pocket money and all the amount
        spent on duties (groceries, rent, communal etc.),
        should be paid off. 
    '''
    if auth.ok(update):
        targets_ok = logic.get_debt_summary(update)
        if targets_ok:
            noreply = context.bot.send_photo(
                chat_id=update.message.chat_id,
                photo = open('debt_summary.png', 'rb')
            )
        time.sleep(10)
        noreply.delete()
        update.message.delete()

def groceries_command(update: Update, context: CallbackContext) -> None:
    if auth.ok(update):
        _, groceries_sum = logic.get_groceries_summary(update, 'eur')
        noreply = update.message.reply_text(
            f'Spent on groceries: {groceries_sum} eur'
        )
        time.sleep(10)
        noreply.delete()
        update.message.delete()

def start_command(update: Update, context: CallbackContext) -> None:
    if update.message.chat_id not in auth.chats():
        auth.update_chats(update.message.chat_id)
    context.job_queue.run_daily(
        dayly_job,
        time = notify_time,
        context=auth.chats
    )

def help_command(update: Update, context: CallbackContext) -> None:
    if auth.ok(update):
        noreply = update.message.reply_markdown_v2(
            f'`help` \- show this message and exit\n'
            f'`expenses` \- show available expenses categories\n'
            f'`pocket` \- show pocket money summary\n'
            f'`groceries` \- show month groceries statistics\n'
            f'`target` \- show targets debt summary\n'
            f'`today` \- show today statistics\n'
            f'`month` \- show month statistics'
        )
        time.sleep(10)
        noreply.delete()
        update.message.delete()

def load_config(config_name: str) -> dict:
    with open(config_name, 'r') as config:
        config = json.load(config)
        return config

def main() -> None:
    tel_config = load_config('telegram.json')
    
    updater = Updater(tel_config['token'], use_context=True)

    updater.job_queue.run_daily(
        dayly_job,
        time = notify_time,
        context=auth.chats()
    )

    dispatcher = updater.dispatcher
    dispatcher.add_handler(CommandHandler("start", start_command))
    dispatcher.add_handler(CommandHandler("help", help_command))
    dispatcher.add_handler(CommandHandler("expenses", expenses_command))
    dispatcher.add_handler(CommandHandler("pocket", pocket_command))
    dispatcher.add_handler(CommandHandler("groceries", groceries_command))
    dispatcher.add_handler(CommandHandler("target", target_command))
    dispatcher.add_handler(CommandHandler("today", day_command))
    dispatcher.add_handler(CommandHandler("month", month_command))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, buy_message))

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()

