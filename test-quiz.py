import sqlite3
import datetime
from datetime import date, timedelta

# Функция создания подписки
def create_subscription(user_id, user_name):
    # Получение текущей даты
    start_date = date.today()

    # Вычисление даты окончания подписки (прибавляем 30 дней к текущей дате)
    end_date = start_date + timedelta(days=30)

    # Подключение к базе данных quiz.db
    conn = sqlite3.connect('quiz.db')
    cursor = conn.cursor()

    try:
        # Создание записи в таблице main_subscribe
        cursor.execute("INSERT INTO main_subscribe (user_id, user_name, start_date, end_date) VALUES (?, ?, ?, ?)",
                       (user_id, user_name, start_date, end_date))

        # Сохранение изменений в базе данных
        conn.commit()

        # Закрытие соединения с базой данных
        conn.close()

        return True  # Успешно создана подписка
    except Exception as e:
        print(f"Ошибка при создании подписки: {e}")
        conn.close()
        return False  # Произошла ошибка при создании подписки



# Функция проверки подписки у пользователя
def check_subscription(user_id):
    # Подключение к базе данных quiz.db
    conn = sqlite3.connect('quiz.db')
    cursor = conn.cursor()

    # Получение текущей даты
    current_date = date.today()

    # Проверка наличия записи в таблице main_subscribe
    cursor.execute("SELECT 1 FROM main_subscribe WHERE user_id = ? AND start_date <= ? AND end_date >= ?", (user_id, current_date, current_date))
    subscription_exists = cursor.fetchone() is not None

    # Закрытие соединения с базой данных
    conn.close()

    return subscription_exists



def check_payment(user_id):
    # Подключение к базе данных quiz.db
    conn = sqlite3.connect('quiz.db')
    cursor = conn.cursor()
    # Получение информации о пользователе
    cursor.execute("SELECT free_limits FROM main_user WHERE user_id = ?", (user_id,))
    free_limits = cursor.fetchone()[0]

    if free_limits > 0:
        # Если у пользователя есть бесплатные лимиты, уменьшаем их на 1
        updated_free_limits = free_limits - 1
        cursor.execute("UPDATE main_user SET free_limits = ? WHERE user_id = ?", (updated_free_limits, user_id))
        conn.commit()
        return True
        # Далее выполните логику по созданию теста
    else:
        # Если у пользователя нет бесплатных лимитов, проверяем подписку
        subscription_active = check_subscription(user_id)
        if subscription_active:
            return True
        else:
            return False



create_subscription(859711206, "seo-darold")


# print(check_payment(859711206))