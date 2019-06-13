# from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler, RegexHandler, \
#     CallbackQueryHandler
# from telegram import ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
# import telegram
import os
import threading
import time
import logging
import traceback
from typing import List
from iface import Viber
import dialog

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

thread = None
dialogs = {}

# Convo states
CHOOSING, TYPING_REPLY, TYPING_CHOICE, INVALID_HELLO = range(4)

reply_keyboard = []
markup = None  # ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)


def get_bots():
    bots = [Viber(os.environ.get("VIBER_HOSTNAME"), web_config=('0.0.0.0', 5000))]
    return bots

def handle_start_greet(bot, update):
    dialog = get_dialog(update.message.chat_id, bot, update)
    # while not done:
    #     m = input('.'.join(r))
    intent_name, entities = parse_intent(update.message.text)
    logging.info("Got intent: %s", intent_name)
    is_valid = False
    if intent_name in ['greet']:
        r = dialog['flow'].greet()
        is_valid = True
        update.message.reply_text(reply(r))

    return CHOOSING if is_valid else INVALID_HELLO


def location(bot, update):
    message = None
    if update.edited_message:
        message = update.edited_message
    else:
        message = update.message
    current_pos = (message.location.latitude, message.location.longitude)
    print(message.location)


def send_img(bot, chat_id, imgreply: Reply, as_group=False):
    from io import BytesIO
    imglist = imgreply.img
    if not isinstance(imglist, list):
        imglist = [imglist]
    if len(imglist) == 1 and not as_group:
        img = imglist[0]
        img_data = img['fetcher'](img['obj'])
        bio = BytesIO(img_data)
        bio.name = 'image.jpeg'
        bio.seek(0)
        bot.send_photo(chat_id, photo=bio)
    else:
        media_group = []
        for img in imglist:
            img_data = img['fetcher'](img['obj'])
            bio = BytesIO(img_data)
            input_photo = InputMediaPhoto(bio, caption='', parse_mode='Markdown')
            media_group.append(input_photo)
        bot.send_media_group(chat_id, media=media_group)


like_lbl = "😃"
dislike_lbl = "💩"


def get_place_keyboard():
    keyboard = [[InlineKeyboardButton(like_lbl, callback_data='confirm'),
                 InlineKeyboardButton(dislike_lbl, callback_data='reject'),
                 InlineKeyboardButton("Show me the 🗺️", callback_data='end')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    return reply_markup


def send_reply(bot, update, replies: List[Reply]):
    """

    :param reply:
    :param bot:
    :param update:
    :return:
    """
    if update.callback_query is not None:
        raise Exception('Callback query can\'t have a reply')
    chat_id = update.message.chat.id
    if not isinstance(replies, list): replies = [replies]
    for rep in replies:
        # logging.info("Got reply type: %s", rep.type)
        # logging.info(rep)
        reply_text = rep.str()
        if reply_text == "": reply_text = "No name"
        # logging.info("Reply text %s", reply_text)
        if rep.type == 'place':
            # Send the image and a button for the user to confirm or reject
            if rep.img:
                send_img(bot, chat_id, rep)
            update.message.reply_text(reply_text, reply_markup=get_place_keyboard())
        elif rep.type == 'place_list':
            logging.info("Reply itinerary: %s", reply_text)
            update.message.reply_text(reply_text, parse_mode=telegram.ParseMode.MARKDOWN)
            for place in rep.data:
                place_text = place['text']
                place_loc = place['location']
                # bot.send_location(chat_id, latitude=float(place_loc['lat']), longitude=float(place_loc['lng']))
                # update.message.reply_text(place_text, parse_mode=telegram.ParseMode.MARKDOWN)
        elif rep.type == 'interest_question':
            # update.message.reply_text(reply_text, parse_mode=telegram.ParseMode.MARKDOWN)
            interests = rep.data
            # custom_keyboard = [[x.capitalize()] for x in interests]
            # reply_markup = ReplyKeyboardMarkup(custom_keyboard, one_time_keyboard=True)
            reply_markup = None
            bot.send_message(chat_id=chat_id, text=reply_text, reply_markup=reply_markup)

        else:
            update.message.reply_text(reply_text)


def send_message(bot, chat_id, rep: Reply):
    reply_text = rep.str()
    if reply_text == "": reply_text = "No name"
    if rep.type == 'place':
        # Place request
        # send the mage and a button for the user to confirm or reject
        if rep.img:
            send_img(bot, chat_id, rep)
        bot.send_message(chat_id, reply_text, reply_markup=get_place_keyboard())
    elif rep.type == 'place_list':
        logging.info("Reply itinerary: %s", reply_text)
        bot.send_message(chat_id, reply_text, parse_mode=telegram.ParseMode.MARKDOWN)
    else:
        bot.send_message(chat_id, reply_text, parse_mode=telegram.ParseMode.MARKDOWN)


#  __________________________ Message handlers ________________________________________________________________

def button(bot, update):
    # logging.info(update)
    # logging.info(bot)
    query = update.callback_query
    chat_id = query.message.chat.id
    dialog = get_dialog(chat_id, bot, update)
    flow = dialog['flow']
    reply_msgs = []
    #
    # logging.info("Button pressed for: %s", update)
    text = query.message.text
    if query.data == 'confirm':
        query.edit_message_text(text="{1} {0}.".format(text, like_lbl))
        done, reply_msgs = flow.confirm()
    elif query.data == 'reject':
        query.edit_message_text(text="{1} {0}.".format(text, dislike_lbl))
        done, reply_msgs = flow.reject()
    elif query.data == 'end':
        query.edit_message_text(text=text)
        done, reply_msgs = flow.end()
    if not isinstance(reply_msgs, list): reply_msgs = [reply_msgs]

    for rep in reply_msgs:
        send_message(bot, chat_id, rep)
    # bot.send_message(chat_id, msg_reply.text)
    # send_reply(bot, update, msg_reply)


def handle_text_message(bot, update):
    dialog = get_dialog(update.message.chat_id, bot, update)
    try:
        done, reply = dialog['flow'].process_message(update.message.text)
        send_reply(bot, update, reply)
    except Exception as err:
        traceback.print_exc()
        update.message.reply_text(text="Crashed while handling this..")
    return CHOOSING


def done(update, context):
    user_data = context.user_data
    if 'choice' in user_data:
        del user_data['choice']
    user_data.clear()
    return ConversationHandler.END


# __________________________________________ Callbacks From Dialog flow

def send_searching_action(details, bot, update):
    chat_id = update.message.chat.id
    logging.info("Starting search at %s", details)
    place = details['location'].capitalize()
    type = details['type']
    if len(type) == 0:
        bot.send_message(chat_id, "Great. Here are a few starting points for you to explore in {0}..".format(place))
    else:
        bot.send_message(chat_id, "Great. I'll start searching for {0}(s) in {1}..".format(type, place))
    bot.send_chat_action(chat_id=chat_id, action=telegram.ChatAction.TYPING)


def send_searching_update(chat_id, bot, update):
    dialog = get_dialog(chat_id, bot, update)
    scount = len(dialog['flow'].get_suggestion_boxes())
    text = ""
    if scount > 0:
        # text = 'I found a total of *{0}* results for you: '.format(scount)
        pass
    else:
        text = 'Sorry I couldn\'t find any results for that.'
    if len(text) > 0:
        bot.send_message(chat_id, text, parse_mode=telegram.ParseMode.MARKDOWN)


def get_dialog(id, bot, update):
    global dialogs
    if id not in dialogs:
        dialogs[id] = empty_dialog(bot, update)
        dialogs[id]['flow'].on_searching(
            lambda details: send_searching_action(details, dialogs[id]['bot'], dialogs[id]['update']))
        dialogs[id]['flow'].on_search_resolved(
            lambda: send_searching_update(id, dialogs[id]['bot'], dialogs[id]['update']))
    return dialogs[id]


def empty_dialog(bot, update):
    return {
        'update': update,
        'bot': bot,
        'state': {},
        'flow': dialog.create_empty()
    }


def run():
    global thread
    thread = threading.Thread(target=start_telegram)
    thread.start()


def start_telegram():
    print("Starting telegram api")
    updater = Updater(token)
    location_handler = MessageHandler(Filters.location, location, edited_updates=True)
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start), MessageHandler(Filters.text, handle_start_greet)],
        states={
            CHOOSING: [MessageHandler(Filters.text, handle_text_message)]
        },
        fallbacks=[RegexHandler('^Done$', done, pass_user_data=True)]
    )
    updater.dispatcher.add_handler(location_handler)
    updater.dispatcher.add_handler(CallbackQueryHandler(button))
    updater.dispatcher.add_handler(conv_handler)
    updater.start_polling()
    print("Telegram bot polling")
    # updater.idle()
    while True:
        time.sleep(1)
