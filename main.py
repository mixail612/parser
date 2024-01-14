import telebot
import threading
import pars
import sys
import time
from data import _db_session
from data.__all_models import Url, ParsToUrl

db_sess = None
tread = None
gui = None

help_message = '''
/help - вывести доступные команды
/start - запуск бота
/stop - остановка бота
/restart - перезапуск бота
/add_url - добавить ссылку
/delete_url - удалить ссылку
/clean_urls - удалить все ссылки
/dir_urls - просмотреть ссылки
'''


_db_session.global_init("db/tests.db")
db_sess = _db_session.create_session()


def get_urls():  # получение ссылок, по которым проводится поиск
    urls = db_sess.query(Url)
    result = []
    for url in urls:
        result.append([url.url, url.id])
    return result


def get_parse_to_urls():  # получение ссылок на старые объявления
    urls = db_sess.query(ParsToUrl)
    result = []
    for url in urls:
        result.append(url.url)
    return result


def add_parse_to_url(url):  # добавление ссылки к ссылкам на старые объявления
    to_url = ParsToUrl()
    to_url.url = url
    db_sess.add(to_url)
    db_sess.commit()


def add_url_to_urls(url):  # добавление ссылки к ссылкам, по которым проводится поиск
    new_url = Url()
    new_url.url = url
    new_url.user_id = user_id
    new_url.do_parse = True
    db_sess.add(new_url)
    db_sess.commit()


with open('config.txt', 'r', encoding='UTF-8') as f:
    lines = f.readlines()
    config = []
    for line in lines[:5]:
        config.append(line.split(': ')[1].rstrip('\n'))
    token = config[0]
    user_id = int(config[1])
    maximum_messages = int(config[2])  # максимальное количество сообщений по 1 ссылке
    delay1 = int(config[3])  # задержка между проверкой ссылки на общее количество ссылок
    delay2 = int(config[4])  # задержка между открытием ссылок


treads = {}
treads_to_joining = []
do_parsing = False
waiting_url = False
deleting_url = False
bot = telebot.TeleBot(token)


def parsing(message, url):  # проверяет наличие новых объявлений по ссылке и если они есть присылает в тг
    while treads[url][1]:
        first_time = time.time()  # засекается время, за которое происходит проверка
        parse_to_urls = get_parse_to_urls()  # получение ссылок на старые объявления
        advs = pars.pars(url, parse_to_urls,gui)  # получение новых объявлений по ссылке
        if advs:
            for adv in advs[:maximum_messages]:
                add_parse_to_url(adv['url'])  # добавление ссылки к старым ссылкам
                if adv["url"] in parse_to_urls:
                    break
                elif adv:
                    bot.send_message(message.chat.id, f'цена: {adv["price"]}\n{adv["url"]}')  # отправка объявления в тг
        num_parsing_urls = len(get_urls())
        if time.time() - first_time < num_parsing_urls * delay1:
            # вычисление зажержки с учетом времени загрузки
            waiting_time = num_parsing_urls * delay1 - (time.time() - first_time)
            # сделанно именно так, чтобы гасить поток не дожидаясь прохождения всей задержки
            for _ in range(num_parsing_urls):
                if treads[url][1]:
                    time.sleep(waiting_time / num_parsing_urls)
                else:
                    break
    del treads[url]  # удаление потока


def waiting_stop(message):  # перезапуск парсера
    bot.send_message(message.chat.id, str(treads))
    for key in treads.keys():
        treads[key][1] = False  # останока потоков
    bot.send_message(message.chat.id, str(treads))
    while treads.values():  # ожидание пока все потоки не удалятся
        pass
    bot.send_message(message.chat.id, str(treads))
    start(message, no_message=True)  # запуск парсера
    bot.send_message(message.chat.id, 'перезапуск завершён.')


@bot.message_handler(commands=['stop'])
def stop(message):  # остановка парсинга
    for key in treads.keys():
        treads[key][1] = False   # останока потоков
    bot.send_message(message.chat.id, 'парсинг остановлен, подождите пока процессы закончятся.')


@bot.message_handler(commands=['start'])
def start(message, no_message=False):  # запуск парсинга
    urls = get_urls()  # получение ссылок
    if any([url[0] in treads.keys() for url in urls]):  # проверка на то, запущен ли парсинг
        if not no_message:
            bot.send_message(message.chat.id, 'парсинг уже запущен')
        else:
            print('error in waiting_stop')
    else:
        if not no_message:
            bot.send_message(message.chat.id, 'парсинг запущен')
        for url in urls:  # создание потоков
            treads[url[0]] = ['', True]
            treads[url[0]] = [threading.Thread(target=parsing, args=(message, url[0],)), True]
        for tread in treads.values():  # запуск потоков
            tread[0].start()
            time.sleep(15)


@bot.message_handler(commands=['add_url'])
def add_url(message):  # добавление ссылки к ссылкам, по которым проводится парсинг.
    global waiting_url
    waiting_url = True  # ожидание сообщения с ссылкой, вторая часть в messages_handler
    bot.send_message(message.chat.id, 'введите ссылку')


@bot.message_handler(commands=['clean_urls'])
def clean_urls(message):  # удаление всех ссылок, по которым проводится парсинг
    urls = db_sess.query(Url)
    for url in urls:
        db_sess.delete(url)
    db_sess.commit()
    bot.send_message(message.chat.id, 'список ссылок очищен, для применения перезапустите бот.')


@bot.message_handler(commands=['dir_urls'])
def dir_urls(message):  # вывод всех ссылок
    urls = get_urls()
    if urls:
        bot.send_message(message.chat.id, '\n'.join([' - '.join(map(str, url[::-1])) for url in urls]))
    else:
        bot.send_message(message.chat.id, 'ссылок нет')


@bot.message_handler(commands=['delete_url'])
def delete_url(message):  # удаление ссылки из ссылок, по которым проводится парсинг
    global deleting_url
    deleting_url = True  # ожидание ссылки для удаления, вторая часть в messages_handler
    bot.send_message(message.chat.id, 'введите номер ссылки')


@bot.message_handler(commands=['restart'])
def restart(message):
    bot.send_message(message.chat.id, 'перезагрузка запущена, ожидайте сообщение.')
    tread = threading.Thread(target=waiting_stop, args=(message,))
    tread.start()
    tread.join()


@bot.message_handler(commands=['help'])
def help(message):
    bot.send_message(message.chat.id, help_message)


@bot.message_handler()
def messages_handler(message):
    global waiting_url, deleting_url
    if waiting_url:  # проверка на то, ожидается ли ссылка на добавление
        add_url_to_urls(message.text)  # добавление ссылки
        bot.send_message(message.chat.id, 'чтобы применить изменения перезапустите бот')
        waiting_url = False
    elif deleting_url:  # проверка на то, ожидается ли ссылка на удаление
        urls = db_sess.query(Url).filter(Url.id == message.text)
        for url in urls:
            db_sess.delete(url)  # удаление ссылки
        db_sess.commit()
        bot.send_message(message.chat.id, 'чтобы применить изменения перезапустите бот')
        deleting_url = False


bot.polling(none_stop=True)
