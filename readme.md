1. Заполнить config.ini своими данными. Изменить хост и порт для подключения к БД, если надо. 
В скрипте используется оффициальный коннектор mysql, на cервере mysql дефолтный порт для подключения с помощью коннектора - 33060
Получить id нужной доски можно вставив в браузере ссылку(заменить апи ключ и токен на свои):

https://api.trello.com/1/members/me/boards?key=Api_key&token=Token

2. Установить зависимости

Windows:

`pip install -r requirements.txt`

Linux:

`pip3 install -r requirements.txt`

3. В конфигурационном файле mysql(на ubuntu20 путь к файлу: /etc/mysql/mysql.conf.d/mysqld.cnf) в секции [mysqld] добавляем следующую строчку

default_authentication_plugin = mysql_native_password

4. Перезапустить mysql

`systemctl restart mysql`

5. Подключится к mysql и создать базу данных

`CREATE DATABASE teletrello DEFAULT CHARACTER SET utf8 DEFAULT COLLATE utf8_general_ci;`

6. Создать пользователя в mysql с привилегиями на БД teletrello(mysql8)

`CREATE USER 'teletrello'@'%' IDENTIFIED WITH mysql_native_password BY 'gAg2J28Kc9';`

`GRANT ALL PRIVILEGES ON teletrello . * TO 'teletrello'@'%';`

`FLUSH PRIVILEGES;`

7. Развернуть дамп dump.sql

`mysql -v -u teletrello -p teletrello < dump.sql`

8. Если в файле config.ini в секции [db] указана sqlite, то пункты от 3 по 7-й включительно не нужны. 
Чтобы использовать mysql установите в секции [db] значение mysql

9. Открыть файл config.py и добавить в секции [trello-workers] чат-ид тех, кто будет выполнять задачи,
 через запятую без пробелов
Получить его можно запустив бота и ввести команду /id
Пример как должно быть:

[trello-workers]

chat_id = 439864728,439864729

10. Запусть скрипт

Windows:

    `py bot.py`
Linux:

    `python3 bot.py`

