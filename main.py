import telebot
import uuid # str(uuid.uuid4())
import random
import time
import json

VERSION = '0.3.2_untested'
TOKEN = json.load(open('token.json', encoding='UTF-8'))
# WORDS = [['слово', 'тема'], ['тестирование', 'проверка']]
WORDS = json.load(open('words.json', encoding='UTF-8'))
TRANSLATE = json.load(open("translate.json", encoding='UTF-8'))
HELP_MESSAGE = TRANSLATE["help_message"]

key_array = ['/k ' + chr(a) for a in range(ord('А'), ord('Я') + 1)] # TODO: More beautiful keyboard (after release)
bonus_array = [0] * 2 + [5] * 5 + [10] * 10 + [15] * 5 + [20] * 3

rooms = {}
busy = {}
top = json.load(open("top.json", encoding='UTF-8'))

bot = telebot.TeleBot(TOKEN)
BOT_NAME = bot.get_me().username
telebot.apihelper.SESSION_TIME_TO_LIVE = 5 * 60


def save_stat():
    with open("top.json", 'w', encoding='UTF-8') as filew:
        json.dump(top, filew, ensure_ascii=False)


def end_of_turn(message, id):
    next_num = rooms[id]['users'].index(rooms[id]['turn']) + 1
    if next_num >= len(rooms[id]['users']):
        next_num = 0
    rooms[id]['turn'] = rooms[id]['users'][next_num]
    user_turn = bot.get_chat_member(id, rooms[id]['turn'])
    marked_username = '[{0}](tg://user?id={1})'.format(user_turn.user.first_name, str(user_turn.user.id))
    rooms[id]['next_score'] = random.choice(bonus_array)
    bot.reply_to(message, TRANSLATE["next_turn"].format(marked_username, 
        rooms[id]['theme'].upper(), rooms[id]['real_word'].replace('.', '\*').upper(), str(rooms[id]['next_score'])), 
        reply_markup=rooms[id]['markup'], parse_mode='Markdown')
    rooms[id]['last_action'] = time.time()


def end_of_game(id):
    statistics = ''
    for user in rooms[id]['users']:
        user_data = bot.get_chat_member(id, user)
        marked_username = '[{0}](tg://user?id={1})'.format(user_data.user.first_name, str(user_data.user.id))
        statistics += " " + marked_username + ': ' + str(rooms[id]['score'][user]) + '\n'
        del busy[user]
        # Top
        if str(user) not in top[str(id)]:
            top[str(id)][str(user)] = 0
        top[str(id)][str(user)] += rooms[id]['score'][user]
    bot.send_message(id, TRANSLATE["end_of_game"].format(rooms[id]['word'], statistics), reply_markup = telebot.types.ReplyKeyboardRemove(), parse_mode='Markdown')
    del rooms[id]
    save_stat()


@bot.message_handler(commands=['version'])
def ver_func(message):
    bot.reply_to(message, VERSION)


@bot.message_handler(commands=['start', 'help'])
def start_func(message):
    if len(message.text.split(' ')) > 1 and message.chat.type == 'private' and message.from_user.id not in list(busy.keys()):
        try:
            id = int(message.text.split(' ')[1])
            if id in list(rooms.keys()):
                if message.from_user.id not in rooms[id]['users']:
                    rooms[id]['score'][message.from_user.id] = 0
                    rooms[id]['users'].append(message.from_user.id)
                    busy[message.from_user.id] = id
                    bot.reply_to(message, TRANSLATE["joined"])
                    marked_username = '[{0}](tg://user?id={1})'.format(message.from_user.first_name, str(message.from_user.id))
                    bot.send_message(id, TRANSLATE["user_joined"].format(marked_username), parse_mode='Markdown')
                else:
                    bot.reply_to(message, TRANSLATE["already_joined"])
        except ValueError:
            bot.reply_to(message, TRANSLATE["error"])
    else:
        bot.reply_to(message, HELP_MESSAGE)


@bot.message_handler(commands=['game'], func=lambda message: message.from_user.id not in list(busy.keys()))
def new_game(message):
    if message.chat.id not in list(rooms.keys()) and (message.chat.type == 'supergroup' or message.chat.type == 'group'):
        room = {
            'id': message.chat.id,
            'users': [],
            'score': {},
            'turn': None,
            'word': 'слово',
            'real_word': '',
            'busy_letter': [],
            'theme': '',
            'status': 'init',
            'last_action': 0,
            'next_score': 0
            # 'markup': MARKUP
        }
        rooms[room['id']] = room
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton(text=TRANSLATE["join_button"], url='https://t.me/'+ BOT_NAME +'?start=' + str(room['id'])))
        bot.reply_to(message, TRANSLATE["join_message"], reply_markup=markup)
    elif message.chat.id in list(rooms.keys()):
        room = rooms[message.chat.id]
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton(text=TRANSLATE["join_button"], url='https://t.me/'+ BOT_NAME +'?start=' + str(room['id'])))
        bot.reply_to(message, TRANSLATE["join_message"], reply_markup=markup)
    else:
        bot.reply_to(message, TRANSLATE["join_error"])


@bot.message_handler(commands=['leave'], func=lambda message: message.from_user.id in list(busy.keys()))
def leave_room(message):
    id = message.chat.id
    if id in list(rooms.keys()):
        if message.from_user.id in rooms[id]['users'] and len(rooms[id]['users']) > 1:
            ind = rooms[id]['users'].index(message.from_user.id)
            if rooms[id]['turn'] == message.from_user.id:
                end_of_turn(message, id)
            del rooms[id]['users'][ind]
            del busy[message.from_user.id]
            marked_username = '[{0}](tg://user?id={1})'.format(message.from_user.first_name, str(message.from_user.id))
            bot.reply_to(message, TRANSLATE["leave"].format(marked_username), parse_mode='Markdown')
        # End of game (no players)
        elif message.from_user.id in rooms[id]['users'] and len(rooms[id]['users']) <= 1:
            end_of_game(id)


@bot.message_handler(commands=['start_game'], func=lambda message: message.from_user.id in list(busy.keys()))
def start_game(message):
    id = message.chat.id
    if id in list(rooms.keys()):
        if message.from_user.id in rooms[id]['users'] and rooms[id]['status'] == 'init':
            rooms[id]['status'] = 'game'
            rooms[id]['word'], rooms[id]['theme'] = WORDS[random.randint(0, len(WORDS) - 1)]
            rooms[id]['turn'] = rooms[id]['users'][0]
            rooms[id]['real_word'] = '.' * len(rooms[id]['word'])
            rooms[id]['last_action'] = time.time()
            # Markup
            markup = telebot.types.ReplyKeyboardMarkup()
            markup.add(*key_array)
            rooms[id]['markup'] = markup
            # 
            for i in range(len(rooms[id]['users'])): rooms[id]['score'][rooms[id]['users'][i]] = 0
            user_turn = bot.get_chat_member(id, rooms[id]['turn'])
            marked_username = '[{0}](tg://user?id={1})'.format(user_turn.user.first_name, str(user_turn.user.id))
            # Top
            if str(id) not in top:
                top[str(id)] = {}
            rooms[id]['next_score'] = random.choice(bonus_array)
            bot.reply_to(message, TRANSLATE["next_turn"].format(marked_username, 
                rooms[id]['theme'].upper(), rooms[id]['real_word'].replace('.', '\*').upper(), str(rooms[id]['next_score'])), 
                reply_markup=rooms[id]['markup'], parse_mode='Markdown')


@bot.message_handler(commands=['k'], func=lambda message: message.from_user.id in list(busy.keys()))
def key(message):
    id = message.chat.id
    if id in list(rooms.keys()):
        if message.from_user.id == rooms[id]['turn']:
            if len(message.text.split(' ')) > 1:
                k = message.text.split(' ')[1].lower()
                word_list = list(rooms[id]['word'])
                if len(k) == 1:
                    if k in word_list and k not in rooms[id]['busy_letter']:
                        prev_letter = -1
                        for letters in range(word_list.count(k)):
                            temp_list = list(rooms[id]['real_word'])
                            temp_list[word_list.index(k, prev_letter + 1, len(word_list) + 1)] = k 
                            prev_letter = word_list.index(k, prev_letter + 1, len(word_list) + 1)
                            rooms[id]['real_word'] = ''.join(temp_list)
                        rooms[id]['score'][message.from_user.id] += word_list.count(k) * rooms[id]['next_score']
                        rooms[id]['busy_letter'].append(k)
                        bot.reply_to(message, TRANSLATE["right_answer"].format(word_list.count(k) * rooms[id]['next_score'], 
                            rooms[id]['score'][message.from_user.id]))
                    else:
                        rooms[id]['busy_letter'].append(k)
                        bot.reply_to(message, TRANSLATE["wrong_answer"])
                    # Markup
                    markup = telebot.types.ReplyKeyboardMarkup()
                    new_key_array = sorted(list(set(key_array) - set(['/k ' + a.upper() for a in rooms[id]['busy_letter']])))
                    markup.add(*new_key_array)
                    rooms[id]['markup'] = markup
                    # End of game
                    if rooms[id]['real_word'] == rooms[id]['word']:
                        end_of_game(id)
                    # End of turn
                    else:
                        end_of_turn(message, id)


@bot.message_handler(commands=['word'], func=lambda message: message.from_user.id in list(busy.keys()))
def word(message):
    id = message.chat.id
    if id in list(rooms.keys()):
        if message.from_user.id == rooms[id]['turn']:
            if len(message.text.split(' ')) > 1:
                if message.text.split(' ')[1].lower() == rooms[id]['word']:
                    rooms[id]['score'][message.from_user.id] += list(rooms[id]['real_word']).count('.') * rooms[id]['next_score']
                    bot.reply_to(message, TRANSLATE["right_answer"].format(list(rooms[id]['real_word']).count('.') * rooms[id]['next_score'], 
                        rooms[id]['score'][message.from_user.id]))
                    # End of game
                    end_of_game(id)
                else:
                    # End of turn
                    bot.reply_to(message, TRANSLATE["wrong_answer"])
                    end_of_turn(message, id)
                return None
    bot.reply_to(message, TRANSLATE["word_error"])


@bot.message_handler(commands=['next'], func=lambda message: message.from_user.id in list(busy.keys()))
def next_turn(message):
    id = message.chat.id
    if id in list(rooms.keys()):
        if rooms[id]['last_action'] < time.time() - 120 and rooms[id]['status'] == 'game':
            end_of_turn(message, id)


@bot.message_handler(commands=['top'], func=lambda message: message.from_user.id not in list(busy.keys()))
def top_func(message):
    id = str(message.chat.id)
    if id not in top:
        top[id] = {}
    unsorted_statistics = []
    for user in list(top[id].keys()):
        try:
            user_data = bot.get_chat_member(int(id), int(user))
            marked_username = '_{0}_'.format(user_data.user.first_name)
            if user_data.user.first_name == '':
                marked_username = '_Неизвестный_'
        except (telebot.apihelper.ApiTelegramException, AttributeError):
            marked_username = '_Неизвестный_'
        unsorted_statistics.append([' ' + marked_username + ': ' + str(top[id][user]) + '\n', top[id][user]])
    unsorted_statistics = sorted(unsorted_statistics, key=lambda a: a[1], reverse=True)
    statistics = ''.join([a[0] for a in unsorted_statistics])
    if statistics == '': statistics = ' Пусто'
    bot.send_message(id, TRANSLATE["top"].format(statistics), parse_mode='Markdown')

while True:
    try:
        bot.polling(timeout=5)
    # except ZeroDivisionError as e:
    except Exception as e:
        print(str(e))
        time.sleep(10)

