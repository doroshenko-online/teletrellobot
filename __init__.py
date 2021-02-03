import configparser
from trello import TrelloClient
import mysql.connector
import sqlite3
import sys
import os
from sys import platform

BASE_PATH = ''

if platform == "linux" or platform == "linux2":
    BASE_PATH = os.getcwd() + '/' + sys.argv[0].replace('bot.py', '')
elif platform == "darwin":
    BASE_PATH = os.getcwd() + '/' + sys.argv[0].replace('bot.py', '')
elif platform == "win32":
    BASE_PATH = os.getcwd() + '\\' + sys.argv[0].replace('bot.py', '')

CONFIG_FILE = BASE_PATH + 'config.ini'
config = configparser.ConfigParser()
config.read(CONFIG_FILE)

ListIdForTasksFromTG = config['trello']['listidfortasksfromtg']
ImportantLabelId = config['trello']['importantlabelid']

# Чат-ид тех, кто будет выполнять задачи
TG_WORKERS_CHAT_ID = config['trello-workers']['chat_id'].split(',')

# Данные телеграмма
TG_TOKEN = config['telegram']['token']

# Данные трелло
TR_API_KEY = config['trello']['api_key']
TR_TOKEN = config['trello']['token']
TR_BOARD_ID = config['trello']['board_id']

# Данные для подключения к БД
if config['db']['db'].strip() == 'mysql':
    MYSQL_HOST = config['mysql']['host']
    if config['mysql']['port'] != '':
        MYSQL_PORT = int(config['mysql']['port'])
    else:
        MYSQL_PORT = 3306
    MYSQL_USER = config['mysql']['user']
    MYSQL_SECRET = config['mysql']['secret']
    MYSQL_DB = config['mysql']['db']

    # Подключение к БД
    conn = mysql.connector.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        user=MYSQL_USER,
        password=MYSQL_SECRET,
        database=MYSQL_DB
    )

    cursor = conn.cursor()


elif config['db']['db'].strip() == 'sqlite':
    SQLITE_DB = BASE_PATH + config['sqlite']['pathtodb']
    conn = sqlite3.connect(SQLITE_DB)
    cursor = conn.cursor()
else:
    raise Exception('В файле config.ini в контексте [db] не указан тип БД или указан не правильно')

# Подключение к трелло
client = TrelloClient(
    api_key=TR_API_KEY,
    token=TR_TOKEN,
)

# Получение объекта доски по ее ид
BOARD = client.get_board(TR_BOARD_ID)
if BOARD.closed:
    print("Доска указання в конфигурации - закрыта")
    sys.exit(1)
BOARD_SHORT_LINK = BOARD.url
