from __init__ import *
import os
import shutil


def get_labels():
    sql = "SELECT * from tr_labels"
    cursor.execute(sql)
    result = cursor.fetchall()

    return result


def get_label(label_id):
    if config['db']['db'].strip() == 'sqlite':
        sql = "SELECT * from tr_labels WHERE label_id=?"
    else:
        sql = "SELECT * from tr_labels WHERE label_id=%s"
    val = (label_id,)
    cursor.execute(sql, val)
    result = cursor.fetchone()

    return result


def get_list(list_id):
    if config['db']['db'].strip() == 'sqlite':
        sql = "SELECT * from tr_dashboard_lists WHERE list_id=?"
    else:
        sql = "SELECT * from tr_dashboard_lists WHERE list_id=%s"
    val = (list_id,)
    cursor.execute(sql, val)
    result = cursor.fetchone()

    return result


def get_list_by_name(list_name):
    if config['db']['db'].strip() == 'sqlite':
        sql = "SELECT * from tr_dashboard_lists WHERE name=?"
    else:
        sql = "SELECT * from tr_dashboard_lists WHERE name=%s"
    val = (list_name,)
    cursor.execute(sql, val)
    result = cursor.fetchone()

    return result


def get_comments(task_id):
    sql = f"SELECT * FROM tr_comments WHERE task_id='{str(task_id)}'"
    cursor.execute(sql)
    return cursor.fetchall()


def get_dashboards_lists():
    sql = "SELECT * from tr_dashboard_lists"
    cursor.execute(sql)
    result = cursor.fetchall()

    return result


def get_tasks():
    sql = "SELECT * from tr_tasks ORDER BY list_id"
    cursor.execute(sql)
    result = cursor.fetchall()

    return result


def get_tasks_by_chat_id(chat_id):
    sql = f"SELECT * FROM tr_tasks WHERE from_user_id='{chat_id}'"
    cursor.execute(sql)
    return cursor.fetchall()


def get_task(task_id):
    if config['db']['db'].strip() == 'sqlite':
        sql = "SELECT * from tr_tasks WHERE task_id=?"
    else:
        sql = "SELECT * from tr_tasks WHERE task_id=%s"
    val = (str(task_id),)
    cursor.execute(sql, val)
    result = cursor.fetchone()

    return result


def insert_dashboard_lists(lists_from_trello):
    for list_tr in lists_from_trello:
        if not get_list(str(list_tr[0])):
            if config['db']['db'].strip() == 'sqlite':
                sql = "INSERT INTO tr_dashboard_lists (list_id, name) VALUES (?, ?)"
            else:
                sql = "INSERT INTO tr_dashboard_lists (list_id, name) VALUES (%s, %s)"
            val = (str(list_tr[0]), str(list_tr[1]))
            cursor.execute(sql, val)
            conn.commit()


def insert_task(task_id, list_id, name, user_id, username, short_link, message_creator_id, files_uid=''):
    if config['db']['db'].strip() == 'sqlite':
        sql = "INSERT INTO tr_tasks (task_id, list_id, task_name, from_user_id, from_user_name, message_creator_id, " \
              "files_uid, short_link) VALUES (?, " \
              "?, ?, ?, ?, ?, ?, ?)"
    else:
        sql = "INSERT INTO tr_tasks (task_id, list_id, task_name, from_user_id, from_user_name, message_creator_id, " \
              "files_uid, short_link) VALUES (%s, " \
              "%s, %s, %s, %s, %s, %s, %s)"
    val = (task_id, list_id, name, user_id, username, message_creator_id, files_uid, short_link)
    cursor.execute(sql, val)
    conn.commit()


def insert_labels(labels_from_trello):
    for label in labels_from_trello:
        if not get_label(str(label[0])):
            if config['db']['db'].strip() == 'sqlite':
                sql = "INSERT INTO tr_labels VALUES (?, ?, ?)"
            else:
                sql = "INSERT INTO tr_labels VALUES (%s, %s, %s)"
            val = (str(label[0]), str(label[1]), str(label[2]))
            cursor.execute(sql, val)
            conn.commit()


def insert_comment(task_id, comment, chat_id, username, files_uid=''):
    if config['db']['db'].strip() == 'sqlite':
        sql = "INSERT INTO tr_comments (task_id, text, files_uid, chat_id, username) VALUES (?, ?, ?, ?, ?)"
    else:
        sql = "INSERT INTO tr_comments (task_id, text, files_uid, chat_id, username) VALUES (%s, %s, %s, %s, %s)"
    val = (task_id, comment, files_uid, str(chat_id), username,)
    cursor.execute(sql, val)
    conn.commit()


def task_change_list(task_id, moved_list_id):
    sql = f"UPDATE tr_tasks SET list_id='{str(moved_list_id)}' WHERE task_id='{str(task_id)}'"
    cursor.execute(sql)
    conn.commit()


def delete_task(task_id):
    task = get_task(task_id)
    if task[6]:
        directory = BASE_PATH + f"files/{task[3]}/{task[6]}"
        if os.path.exists(directory):
            shutil.rmtree(directory)
    if config['db']['db'].strip() == 'sqlite':
        sql = "DELETE FROM tr_tasks WHERE task_id=?"
    else:
        sql = "DELETE FROM tr_tasks WHERE task_id=%s"
    val = (task_id,)
    cursor.execute(sql, val)
    conn.commit()
    comments = get_comments(task_id)
    for comm in comments:
        if comm[3]:
            directory = BASE_PATH + f"files/{comm[4]}/{comm[3]}"
            if os.path.exists(directory):
                shutil.rmtree(directory)
    delete_comments(task_id)


def trunc_lists():
    sql = "delete from tr_dashboard_lists"
    cursor.execute(sql)
    conn.commit()


def trunc_labels():
    sql = "delete from tr_labels"
    cursor.execute(sql)
    conn.commit()


def delete_comments(task_id):
    sql = f"DELETE FROM tr_comments WHERE task_id='{str(task_id)}'"
    cursor.execute(sql)
    conn.commit()
