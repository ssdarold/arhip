# -*- coding: utf-8 -*-

from aiogram import Bot, types
from aiogram.dispatcher import Dispatcher
from aiogram.utils import executor
import logging
import sqlite3
import datetime
from datetime import date, timedelta
from aiogram.dispatcher import FSMContext
from collections import Counter
from aiogram.types import InputFile
from yookassa import Configuration, Payment
import uuid
import asyncio


bot = Bot(token="", proxy="http://proxy.server:3128")
dp = Dispatcher(bot)

YUKASSA_SECRET_KEY = ""
YUKASSA_SHOP_ID = ""

# ================ Кнопки ==============

start_test_button = types.InlineKeyboardButton(text="Пройти тест", callback_data="start_test")
subscribe_button = types.InlineKeyboardButton(text="Оформить подписку", callback_data="subscribe")
process_subscribe_button = types.InlineKeyboardButton(text="Оформить", callback_data="process_subscribe")
cancel_button = types.InlineKeyboardButton("Вернуться в главное меню", callback_data="cancel")
invite_link_button = types.InlineKeyboardButton("Пригласить друга", callback_data="invite_link")
buy_compat_button = types.InlineKeyboardButton("Купить 1 проверку совместимости", callback_data="buy_compat")
process_compat_button = types.InlineKeyboardButton("Оплатить", callback_data="process_buy_compat")

profile_button = types.InlineKeyboardButton("Профиль", callback_data="get_profile")
my_subscribes_button = types.InlineKeyboardButton("Мои подписки", callback_data="get_subscribes")
my_archetype_button = types.InlineKeyboardButton("Мой архетип", callback_data="get_archetype")

# ================ Конец кнопок ==============



# ================ Блок функций ==============

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

# Функция проверки наличия изображений в ответах к вопросу
def check_answer_images_exist(rows):

    for id, text, image in rows:
        if image:
            return True # Картинки есть
        else:
            return False # Картинок нет

def most_frequent(List):
    counter = 0
    num = List[0]
     
    for i in List:
        curr_frequency = List.count(i)
        if(curr_frequency> counter):
            counter = curr_frequency
            num = i
 
    return num

# Определение архетипа
async def get_arch_id(test_id):
    conn = sqlite3.connect('quiz.db')
    cursor = conn.cursor()

    cursor.execute("SELECT answer_id_id FROM main_test_process WHERE test_id_id = ?", (test_id,))
    res = cursor.fetchall()

    archetypes = []

    for i in res:
        ans_id = i[0]
        cursor.execute("SELECT first_arch_id_id FROM main_answer WHERE id = ?", (ans_id,))
        first_arch = cursor.fetchall()[0][0]
        archetypes.append(first_arch)
        cursor.execute("SELECT second_arch_id_id FROM main_answer WHERE id = ?", (ans_id,))
        second_arch = cursor.fetchall()[0][0]
        archetypes.append(second_arch)

    return most_frequent(archetypes)


# Функция для подведения итогов тестирования
async def get_test_summary(user_id, test_id):

    # Очистка предыдущих сообщений
    if messages_for_delete:
        for delete_message_id in messages_for_delete:
            await bot.delete_message(user_id, delete_message_id)

        messages_for_delete.clear()
    # Подключаемся к SQLite базе данных
    conn = sqlite3.connect('quiz.db')
    cursor = conn.cursor()

    # Меняем статус с pending на completed в таблице main_tests
    cursor.execute("UPDATE main_test SET status = 'completed' WHERE id = ?", (test_id,))
    conn.commit()

    # Определяем архетип-победитель
    archetype_id = await get_arch_id(test_id)

    # Записываем в базу, в таблицу main_users, значение архетипа
    cursor.execute("UPDATE main_user SET archetype_id = ? WHERE user_id = ?", (archetype_id, user_id))
    conn.commit()

    # Извлекаем данные об архетипе из таблицы main_archetype
    cursor.execute("SELECT archetype_name, archetype_description FROM main_archetype WHERE id = ?", (archetype_id,))
    archetype_name, archetype_description = cursor.fetchone()

    summary_markup = types.InlineKeyboardMarkup()
    summary_markup.add(cancel_button)
    # Отправляем пользователю сообщение с результатами теста
    await bot.send_message(user_id, archetype_description, reply_markup=summary_markup)

    # Проверяем, есть ли связанный пользователь
    cursor.execute("SELECT first_user_id FROM main_test WHERE id = ?", (test_id,))
    result = cursor.fetchone()


    # Проверяем, что результат запроса не равен None
    if result[0] is not None:
        first_user_id = result[0]


        # Получаем архетип первого пользователя
        cursor.execute('SELECT archetype_id FROM main_user WHERE user_id = ?', (first_user_id,))
        first_user_archetype_id = cursor.fetchone()[0]

        # Находим совместимость архетипов
        cursor.execute("SELECT first_user_description FROM main_сompatibility WHERE "
                    "(first_arch_id = ? AND second_arch_id = ?) OR (first_arch_id = ? AND second_arch_id = ?)",
                    (first_user_archetype_id, archetype_id, archetype_id, first_user_archetype_id))
        first_user_description = cursor.fetchone()[0]

        # Получаем информацию о пользователях
        cursor.execute("SELECT user_name FROM main_user WHERE user_id = ?", (user_id,))
        user_name = cursor.fetchone()[0]

        cursor.execute("SELECT user_name FROM main_user WHERE user_id = ?", (first_user_id,))
        first_user_name = cursor.fetchone()[0]

        # Получаем архетип первого пользователя
        cursor.execute("SELECT archetype_name FROM main_archetype WHERE id = ?", (first_user_archetype_id,))
        first_user_archetype_name = cursor.fetchone()[0]

        # Отправляем информацию о совместимости текущему пользователю
        await bot.send_message(user_id, f"Ваша совместимость готова. Архетип пользователя {first_user_name} - {first_user_archetype_name}. Ваш архетип - {archetype_name}. {first_user_description}.")

        # Отправляем информацию о совместимости инициатору
        await bot.send_message(first_user_id, f"Ваша совместимость готова. Архетип пользователя {user_name} - {archetype_name}. Ваш архетип - {first_user_archetype_name}. {first_user_description}.")

    # Закрываем соединение с базой данных
    conn.commit()
    conn.close()


# Глобальный список для хранения сообщений, которые нужно удалить
messages_for_delete = []




# Функция для обработки ответов пользователя на тест
@dp.callback_query_handler(lambda callback_query: callback_query.data.startswith('handleanswer_'))
async def handle_answer(callback_query: types.CallbackQuery, state: FSMContext):

    input_callback_data = callback_query.data.split('_')

    test_id = input_callback_data[1]
    question_id = input_callback_data[2]
    answer_id = input_callback_data[3]

    # Подключение к базе данных
    conn = sqlite3.connect('quiz.db')
    cursor = conn.cursor()


    # Получение первого архетипа
    cursor.execute("SELECT first_arch_id_id FROM main_answer WHERE question_id = ?", (question_id,))
    first_arch = cursor.fetchone()[0]

    # Получение второго архетипа
    cursor.execute("SELECT second_arch_id_id FROM main_answer WHERE question_id = ?", (question_id,))
    second_arch = cursor.fetchone()[0]

    try:
        # Создание записи в таблице main_test_process
        cursor.execute("INSERT INTO main_test_process (answer_id_id, first_arch_id_id, question_id_id, second_arch_id_id, test_id_id) VALUES (?, ?, ?, ?, ?)",
                        (answer_id, first_arch, question_id, second_arch, test_id))
        conn.commit()




        await test_process(callback_query.from_user.id, test_id)


        # Закрываем соединение с базой данных
        conn.close()

    except sqlite3.Error as e:
        print(f"Ошибка базы данных: {e}")


# Обработчик для кнопки "Шаг назад"
@dp.callback_query_handler(lambda callback_query: callback_query.data.startswith('backtoquestion_'))
async def back_to_question(callback_query: types.CallbackQuery):
    # Извлекаем значения test_id и current_question из callback_query.data

    back_callback_data = callback_query.data.split('_')

    test_id = back_callback_data[1]
    current_question = back_callback_data[2]

    # Преобразуем их в целочисленный формат
    test_id = int(test_id)
    current_question = int(current_question)

    # Подключение к базе данных
    conn = sqlite3.connect('quiz.db')
    cursor = conn.cursor()

    # Вычитаем 1 из current_question
    new_question_id = current_question - 1

    # Удаляем запись из таблицы main_test_process
    cursor.execute("DELETE FROM main_test_process WHERE test_id_id = ? AND question_id_id = ?", (test_id, new_question_id))

    conn.commit()

    await test_process(callback_query.from_user.id, test_id)

    # # Получение id нового вопроса
    # cursor.execute('SELECT id FROM main_question WHERE "order" = ?', (new_question_id,))
    # question_id = cursor.fetchone()[0]
    
    # # Получение текста нового вопроса
    # cursor.execute('SELECT text FROM main_question WHERE "order" = ?', (new_question_id,))
    # question_text = cursor.fetchone()[0]


    # # Получение вариантов ответа для текущего вопроса
    # cursor.execute("SELECT id, text, answer_image FROM main_answer WHERE question_id = ?", (question_id,))
    # answers = cursor.fetchall()


    # # # Отправка вопроса и вариантов ответа
    # await send_question_and_answers(callback_query.from_user.id, test_id, question_id, question_text, answers)

    # # Отвечаем на callback_query, чтобы избежать ошибки
    # await callback_query.answer()



# Функция для отправки вопросов и вариантов ответа
async def send_question_and_answers(user_id, test_id, current_question, question_text, answers):

    conn = sqlite3.connect('quiz.db')
    cursor = conn.cursor()

    # Извлекаем из базы количество вопросов
    cursor.execute("SELECT COUNT(*) FROM main_question")

    # Сохраняем количество вопрсов в переменную
    all_questions = cursor.fetchone()[0]

    conn.close()

    # Очистка предыдущих сообщений
    if messages_for_delete:
        for delete_message_id in messages_for_delete:
            await bot.delete_message(user_id, delete_message_id)

        messages_for_delete.clear()


    markup = types.InlineKeyboardMarkup(row_width=2)
    back_button = types.InlineKeyboardButton("На шаг назад", callback_data=f"backtoquestion_{test_id}_{current_question}")
    main_menu_button = types.InlineKeyboardButton("Вернуться в главное меню", callback_data=f"cancel")

    answer_buttons = []
    answers_text = "Выберите вариант ответа:\n\n\n"
    counter = 1
    # Если изображения есть в ответах
    if check_answer_images_exist(answers):

        # Отправка вариантов ответа
        for answer_id, answer_text, answer_image in answers:
            # answer_markup = types.InlineKeyboardMarkup()
            # answer_button = types.InlineKeyboardButton(answer_text, callback_data=f"handleanswer_{test_id}_{current_question}_{answer_id}")
            # answer_markup.add(answer_button)
    
            if answer_image.endswith('.gif'):
                image_url = InputFile(answer_image)
    
                # Если изображение - gif, используем метод send_animation
                msg = await bot.send_animation(user_id, image_url, caption=f"{answer_text} (Рисунок {counter})")
                messages_for_delete.append(msg.message_id) # Добавляем id сообщения в список на удаление
            else:
                image_url = InputFile(answer_image)
                # Иначе, используем метод send_photo
                msg = await bot.send_photo(user_id, image_url, caption=f"{answer_text} (Рисунок {counter})")
                messages_for_delete.append(msg.message_id) # Добавляем id сообщения в список на удаление
    
            answers_text += f"<b>{counter}</b>. {answer_text} <b><i>(см. Рисунок {counter})</i></b> \n\n"
    
            answer_button = types.InlineKeyboardButton(counter, callback_data=f"handleanswer_{test_id}_{current_question}_{answer_id}")
            # markup.add(answer_button)
            answer_buttons.append(answer_button)
    
            counter += 1
    
        markup.add(*answer_buttons)
        # Если вопрос не первый - добавляем кнопку "Шаг назад". Если первый - не добавляем
        if current_question == 1:
            markup.add(main_menu_button)
        else:
            markup.add(back_button, main_menu_button)
    
        full_question_text = f"""Вопрос {current_question} из {all_questions}\n\n\n<b>{question_text}</b>\n\n\n{answers_text}"""
        # Отправка текущего вопроса
        main_msg = await bot.send_message(user_id, full_question_text, reply_markup=markup, parse_mode="HTML")
        messages_for_delete.append(main_msg.message_id) # Добавляем id сообщения в список на удаление


            
    # Если изображений в ответах нет
    else:

        for answer_id, answer_text, answer_image in answers:
            # answer_button = types.InlineKeyboardButton(answer_text, callback_data=f"handleanswer_{test_id}_{current_question}_{answer_id}")
            # markup.add(answer_button)

            answers_text += f"<b>{counter}</b>. {answer_text} \n\n"

            answer_button = types.InlineKeyboardButton(counter, callback_data=f"handleanswer_{test_id}_{current_question}_{answer_id}")
            # markup.add(answer_button)
            answer_buttons.append(answer_button)

            counter += 1

        markup.add(*answer_buttons)
        if current_question == 1:
            markup.add(main_menu_button)
        else:
            markup.add(back_button, main_menu_button)

        full_question_text = f"""Вопрос {get_current_question_index(test_id) + 1} из {all_questions}\n\n\n<b>{question_text}</b>\n\n\n{answers_text}

"""
        msg = await bot.send_message(user_id, full_question_text, reply_markup=markup, parse_mode="HTML")
        messages_for_delete.append(msg.message_id) # Добавляем id сообщения в список на удаление

    # # Отправляем inline-кнопки с вариантами ответа
    # await bot.send_message(user_id, "Выберите ответ:", reply_markup=markup)

# Функция для обработки теста
async def test_process(user_id, test_id):
    # Подключение к базе данных
    conn = sqlite3.connect('quiz.db')
    cursor = conn.cursor()

    # # Получение теста пользователя с статусом 'pending', если есть
    # cursor.execute("SELECT id FROM main_test WHERE user_id = ? AND status = 'pending'", (user_id,))
    # test_row = cursor.fetchone()

    # test_id = test_row[0] # Получаем id теста

    # Извлекаем из базы количество вопросов
    cursor.execute("SELECT COUNT(*) FROM main_question")

    # Сохраняем количество вопрсов в переменную
    all_questions_count = cursor.fetchone()[0]

    # # Получаем количество пройденных вопросов в рамках текущего теста
    current_question_index = get_current_question_index(test_id)

    # Если количество пройденных вопросов менее общего количества вопросов, получаем следующий вопрос
    if current_question_index < all_questions_count:

        # Определяем порядковый номер следующего запроса
        test_answer_count = current_question_index + 1


        # # Получение id нового вопроса из базы
        # cursor.execute("SELECT id FROM main_question WHERE order = ?", (test_answer_count,))
        # question_id = cursor.fetchone()[0]

        # Получение id нового вопроса
        cursor.execute('SELECT id FROM main_question WHERE "order" = ?', (test_answer_count,))
        question_id = cursor.fetchone()[0]
        
        # Получение текста нового вопроса
        cursor.execute('SELECT text FROM main_question WHERE "order" = ?', (test_answer_count,))
        question_text = cursor.fetchone()[0]


        # Получение вариантов ответа для текущего вопроса
        cursor.execute("SELECT id, text, answer_image FROM main_answer WHERE question_id = ?", (question_id,))
        answers = cursor.fetchall()


        # # Отправка вопроса и вариантов ответа
        await send_question_and_answers(user_id, test_id, question_id, question_text, answers)

    # Если количество пройденных вопросов более или равно количеству пройденных тестов, то подводим итоги теста
    else:
        await get_test_summary(user_id, test_id)


    # Закрытие соединения с базой данных
    conn.close()


# Функция для получения порядкового номера текущего вопроса в процессе тестирования
def get_current_question_index(test_id):
    # Подключение к базе данных
    conn = sqlite3.connect('quiz.db')
    cursor = conn.cursor()

    # Запрос для получения количества записей с заданным test_id в таблице main_test_process
    cursor.execute("SELECT COUNT(*) FROM main_test_process WHERE test_id_id = ?", (test_id,))
    result = cursor.fetchone()

    if result:
        return result[0]  # Возвращаем количество записей (текущий индекс вопроса)
    else:
        return 0  # Если записей нет, возвращаем 0


# Функция проверки оплаты
async def check_payment(user_id):
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

# Функция для начала нового теста и вызова функции test_process
async def start_new_test(user_id, first_user_id=None):

    if await check_payment(user_id):
        try:
            # Подключение к базе данных
            conn = sqlite3.connect('quiz.db')
            cursor = conn.cursor()

            # Получение текущей даты и времени
            current_datetime = datetime.datetime.now()

            if first_user_id is not None:
                # Создание записи в таблице main_test
                cursor.execute("INSERT INTO main_test (user_id, date_time, status, first_user_id) VALUES (?, ?, ?, ?)",
                            (user_id, current_datetime, 'pending', first_user_id))

                conn.commit()

                test_id = cursor.lastrowid # Получаем id вновь созданного теста

            else:
                # Создание записи в таблице main_test
                cursor.execute("INSERT INTO main_test (user_id, date_time, status) VALUES (?, ?, ?)",
                            (user_id, current_datetime, 'pending'))

                conn.commit()

                test_id = cursor.lastrowid # Получаем id вновь созданного теста



            # Закрытие соединения
            conn.close()

            # Вызов функции test_process с переданным user_id
            await test_process(user_id, test_id)

            # await bot.send_message(user_id, f"Дошли до места вызова test_process. Test id = {test_id}")

            return True  # Успешно начат новый тест

        except Exception as e:
            print(f"Ошибка при начале нового теста: {e}")
            return False  # Произошла ошибка

    else:
        error_payment_markup = types.InlineKeyboardMarkup()
        error_payment_markup.add(subscribe_button, cancel_button)

        await bot.send_message(user_id, "У вас нет активных подписок.", reply_markup=error_payment_markup)

# Функция создания платежа в юкассе
def create_yukassa_payment(amount, description, user_id):
    Configuration.account_id = YUKASSA_SHOP_ID
    Configuration.secret_key = YUKASSA_SECRET_KEY

    payment = Payment.create({
        "amount": {
            "value": str(amount),
            "currency": "RUB"
        },
        "confirmation": {
            "type": "redirect",
            "return_url": "https://kirillporyadin88.pythonanywhere.com",  # URL для перехода после оплаты
        },
        "capture": True,
        "description": description,
        "metadata": {
            "user_id": user_id,
        },
    }, uuid.uuid4())

    return payment


# Оформление подписки
@dp.callback_query_handler(lambda callback_query: callback_query.data == "process_subscribe")
async def process_subscribe(callback_query: types.CallbackQuery):

    # Создаем ссылку на оплату
    payment_response = create_yukassa_payment(1000, f"Оформление подписки на 30 дней", callback_query.from_user.id)

    if payment_response.id:

        # Генерирование inline-кнопки для оплаты
        payment_link = payment_response.confirmation.confirmation_url

        await bot.send_message(callback_query.from_user.id, f'Перейдите по ссылке для оплаты: {payment_link}')

        # Запуск фоновой задачи для обработки платежа
        async def background_payment_task(user_id, payment_response):
            while True:
                # Получаем информацию о платеже
                payment_info = Payment.find_one(payment_response.id)

                # Платеж успешен
                if payment_info.status == 'succeeded':
                    metadata = payment_info.metadata
                    user_id = metadata.get('user_id')

                    success_subscribe_markup = types.InlineKeyboardMarkup()
                    success_subscribe_markup.add(start_test_button, invite_link_button)
                    success_subscribe_markup.add(cancel_button)

                    await bot.send_message(user_id, f"Поздравляем! Подписка оформлена! Теперь вы можете использовать все возможности бота в течение месяца.", reply_markup=success_subscribe_markup)

                    # Создаем подписку
                    create_subscription(user_id, callback_query.from_user.username)
                    break

                # Платеж отменен
                elif payment_info.status == 'canceled':
                    await bot.send_message(callback_query.from_user.id, f"Платеж отменен.")
                    break

                # Автоматическое подтверждение платежа
                elif payment_info.status == 'waiting_for_capture':
                    idempotence_key = str(uuid.uuid4())
                    response = Payment.capture(
                        payment_response.id,
                        {
                            "amount": {
                                "value": "1000.00",
                                "currency": "RUB"
                            }
                        },
                        idempotence_key)
                else:
                    await asyncio.sleep(1)  # Добавим паузу, чтобы не блокировать цикл

        payment_task = asyncio.create_task(background_payment_task(callback_query.from_user.id, payment_response))



# Покупка одной совместимости
@dp.callback_query_handler(lambda callback_query: callback_query.data == "process_buy_compat")
async def process_subscribe(callback_query: types.CallbackQuery):

    # Создаем ссылку на оплату
    payment_response = create_yukassa_payment(300, f"Покупка проверки совместимости архетипов", callback_query.from_user.id)

    if payment_response.id:

        # Генерирование inline-кнопки для оплаты
        payment_link = payment_response.confirmation.confirmation_url

        await bot.send_message(callback_query.from_user.id, f'Перейдите по ссылке для оплаты: {payment_link}')

        # Запуск фоновой задачи для обработки платежа
        async def background_payment_task(user_id, payment_response):
            while True:
                # Получаем информацию о платеже
                payment_info = Payment.find_one(payment_response.id)

                # Платеж успешен
                if payment_info.status == 'succeeded':
                    metadata = payment_info.metadata
                    user_id = metadata.get('user_id')

                    success_subscribe_markup = types.InlineKeyboardMarkup()
                    success_subscribe_markup.add(start_test_button, invite_link_button)
                    success_subscribe_markup.add(cancel_button)


                    invite_link = f'https://t.me/arhip_quiz_bot?start={user_id}'
                    await bot.send_message(user_id, f'Оплата прошла успешно! Ваша уникальная ссылка для приглашения: {invite_link}. Отправьте её тому, с кем хотите проверить совместимость. Результат придёт вам сразу как только приглашенный пользователь пройдет тест.', reply_markup=success_subscribe_markup)

                    break

                # Платеж отменен
                elif payment_info.status == 'canceled':
                    await bot.send_message(callback_query.from_user.id, f"Платеж отменен.")
                    break

                # Автоматическое подтверждение платежа
                elif payment_info.status == 'waiting_for_capture':
                    idempotence_key = str(uuid.uuid4())
                    response = Payment.capture(
                        payment_response.id,
                        {
                            "amount": {
                                "value": "1000.00",
                                "currency": "RUB"
                            }
                        },
                        idempotence_key)
                else:
                    await asyncio.sleep(1)  # Добавим паузу, чтобы не блокировать цикл

        payment_task = asyncio.create_task(background_payment_task(callback_query.from_user.id, payment_response))

# ================ Конец блока функций ==============



# Обработка для команды /start
@dp.message_handler(commands=['start'])
async def on_start(message: types.Message):
    # Получаем значение параметра start_payload из команды /start
    first_user_id = message.get_args() # Получаем id первого пользователя в случае, если имеет место приглашение

    # Получение id текущего пользователя
    current_user_id = message.from_user.id

    # Получение username текущего пользователя
    username = message.from_user.username

    # Получение текущей даты и времени
    current_datetime = datetime.datetime.now()

    # Подключение к базе данных
    conn = sqlite3.connect('quiz.db')
    cursor = conn.cursor()

    # Проверяем, сохранен ли уже наш пользователь в базу
    cursor.execute("SELECT COUNT(*) FROM main_user WHERE user_id = ?", (current_user_id,))
    current_user_count = cursor.fetchone()[0]

    if current_user_count == 0:

        # Создание записи в таблице main_user
        cursor.execute("INSERT INTO main_user (user_id, user_name, signup_date, free_limits) VALUES (?, ?, ?, ?)",
                        (current_user_id, username, current_datetime, 2))

    # Сохранение изменений и закрытие соединения
    conn.commit()

    # Если пришел приглашенный пользователь, сохораняем id инициатора в контекст
    if first_user_id:

        related_markup = types.InlineKeyboardMarkup()
        check_compat_button = types.InlineKeyboardButton("Узнать совместимость", callback_data=f"checkcompat_{first_user_id}_{current_user_id}")
        start_related_test_button = types.InlineKeyboardButton("Пройти тест", callback_data=f"startrelatedtest_{first_user_id}_{current_user_id}")


        # Проверяем, есть ли архетип у текущего пользователя
        cursor.execute("SELECT archetype_id FROM main_user WHERE user_id = ?", (current_user_id,))
        current_user_archetype = cursor.fetchone()[0]

        # Если архетип задан (не NULL)
        if current_user_archetype:

            related_markup.add(check_compat_button)
            hello_text = """🌙 Добро пожаловать в мир удивительных архетипов! 🌙\n\nВ нашем мире очень важно понять свой психотип для того, чтобы понять, в какую сторону двигаться по жизни. Пройди тест и я помогу тебе определить свою идентичность. \n\nВас пригласили для определения совместимости. Вы уже проходили тест, поэтому можете узнать совместимость прямо сейчас!"""


        else:
            related_markup.add(start_related_test_button)
            hello_text = """🌙 Добро пожаловать в мир удивительных архетипов! 🌙 \n\nВ нашем мире очень важно понять свой психотип для того, чтобы понять, в какую сторону двигаться по жизни. Пройди тест и я помогу тебе определить свою идентичность. \n\nВас пригласили для определения совместимости. Сперва вам необходимо узнать свой архетип. Пройдите тест и узнайте, насколько вы совместимы"""

        await bot.send_message(current_user_id, hello_text, reply_markup=related_markup)

    else:

        kb = types.InlineKeyboardMarkup(row_width=2)
        kb.add(
            start_test_button, invite_link_button
        )
        kb.add(
            profile_button
        )

        await message.reply("""🌙 Добро пожаловать в мир удивительных архетипов! 🌙\n\nВ нашем мире очень важно понять свой психотип для того, чтобы понять, в какую сторону двигаться по жизни. Пройди тест и я помогу тебе определить свою идентичность. """, reply_markup=kb)

        conn.close()


# Обработчик для инициализации теста для связанных пользователей
@dp.callback_query_handler(lambda callback_query: callback_query.data.startswith('startrelatedtest_'))
async def cmd_set_main(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id

    related_callback_data = callback_query.data.split('_')

    first_user_id = related_callback_data[1]

    # Если нет не законченных тестов, вызываем функцию start_new_test()
    await start_new_test(user_id, first_user_id)


# Обработчик для проверки совместимости
@dp.callback_query_handler(lambda callback_query: callback_query.data.startswith('checkcompat_'))
async def cmd_set_main(callback_query: types.CallbackQuery):

    # Подключение к базе данных
    conn = sqlite3.connect('quiz.db')
    cursor = conn.cursor()

    user_id = callback_query.from_user.id

    related_callback_data = callback_query.data.split('_')

    first_user_id = related_callback_data[1]
    second_user_id = related_callback_data[2]

    # Получаем архетип первого пользователя
    cursor.execute("SELECT archetype_id FROM main_user WHERE user_id = ?", (first_user_id,))
    first_user_archetype_id = cursor.fetchone()[0]

    # Получаем архетип второго пользователя
    cursor.execute("SELECT archetype_id FROM main_user WHERE user_id = ?", (second_user_id,))
    second_user_archetype_id = cursor.fetchone()[0]

    # Находим совместимость архетипов
    cursor.execute("SELECT first_user_description FROM main_сompatibility WHERE (first_arch_id = ? AND second_arch_id = ?) OR (first_arch_id = ? AND second_arch_id = ?)",
                (first_user_archetype_id, second_user_archetype_id, second_user_archetype_id, first_user_archetype_id))
    first_user_description = cursor.fetchone()[0]

    # Получаем информацию о пользователях
    cursor.execute("SELECT user_name FROM main_user WHERE user_id = ?", (user_id,))
    user_name = cursor.fetchone()[0]

    cursor.execute("SELECT user_name FROM main_user WHERE user_id = ?", (first_user_id,))
    first_user_name = cursor.fetchone()[0]

    # Получаем архетип первого пользователя
    cursor.execute("SELECT archetype_name FROM main_archetype WHERE id = ?", (first_user_archetype_id,))
    first_user_archetype_name = cursor.fetchone()[0]

    # Получаем архетип текущего пользователя
    cursor.execute("SELECT archetype_name FROM main_archetype WHERE id = ?", (second_user_archetype_id,))
    second_user_archetype_name = cursor.fetchone()[0]
    
    comp_markup = types.InlineKeyboardMarkup()
    comp_markup.add(cancel_button)

    # Отправляем информацию о совместимости текущему пользователю
    await bot.send_message(user_id, f"Ваша совместимость готова. Архетип пользователя {first_user_name} - {first_user_archetype_name}. Ваш архетип - {second_user_archetype_name}. {first_user_description}.", reply_markup=comp_markup)

    # Отправляем информацию о совместимости инициатору
    await bot.send_message(first_user_id, f"Ваша совместимость готова. Архетип пользователя {user_name} - {second_user_archetype_name}. Ваш архетип - {first_user_archetype_name}. {first_user_description}.", reply_markup=comp_markup)


# Функция для возврата в главное меню и отмены оплаты
@dp.callback_query_handler(lambda query: query.data == "cancel")
async def cancel_state(query: types.CallbackQuery, state: FSMContext):
    await state.finish()

    main_menu_kb = types.InlineKeyboardMarkup(row_width=2)
    main_menu_kb.add(
        start_test_button, invite_link_button, profile_button
    )
    await query.message.answer("Главное меню", reply_markup=main_menu_kb)
    await query.answer()  # Отправляем пустой ответ, чтобы убрать "часики" с кнопки


# Обработчик для генерации ссылки
@dp.callback_query_handler(lambda callback_query: callback_query.data == "invite_link")
async def generate_invite_link(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id

    if await check_payment(user_id):

        # Подключение к базе данных
        conn = sqlite3.connect('quiz.db')
        cursor = conn.cursor()

        # Проверка наличия не законченного теста для данного пользователя
        cursor.execute("SELECT id FROM main_test WHERE user_id = ? AND status = 'pending'", (user_id,))
        test_id = cursor.fetchone()

        if test_id:
            invite_markup = types.InlineKeyboardMarkup()
            invite_markup.add(types.InlineKeyboardButton("Продолжить тест", callback_data=f"continue_test_{test_id}"))
            await bot.send_message(user_id, "Перед приглашением пользователя необходимо закончить прохождение теста", reply_markup=invite_markup)

        else:
            invite_link = f'https://t.me/arhip_quiz_bot?start={user_id}'
            await bot.send_message(user_id, f'Ваша уникальная ссылка для приглашения: {invite_link}. Отправьте её тому, с кем хотите проверить совместимость.')

    else:
        error_payment_markup = types.InlineKeyboardMarkup()
        error_payment_markup.add(subscribe_button, cancel_button)
        error_payment_markup.add(buy_compat_button)

        await bot.send_message(user_id, "У вас нет активных подписок.", reply_markup=error_payment_markup)


# Обработчик для инициализации теста
@dp.callback_query_handler(lambda callback_query: callback_query.data == "start_test")
async def cmd_set_main(callback_query: types.CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id

    # Подключение к базе данных
    conn = sqlite3.connect('quiz.db')
    cursor = conn.cursor()

    # Проверка наличия не законченного теста для данного пользователя
    cursor.execute("SELECT id FROM main_test WHERE user_id = ? AND status = 'pending'", (user_id,))
    test_row = cursor.fetchone()

    if test_row:
        test_id = test_row[0]
        not_finished_markup = types.InlineKeyboardMarkup()
        not_finished_markup.add(types.InlineKeyboardButton("Продолжить тест", callback_data=f"continue_test_{test_id}"), types.InlineKeyboardButton("Начать с начала", callback_data=f"start_new_test"))
        not_finished_markup.add(types.InlineKeyboardButton("Вернуться в главное меню", callback_data=f"cancel"))

        # Если есть не законченный тест, отправляем сообщение с вариантами действий
        await callback_query.message.answer(
            "У вас есть один не законченный тест. Желаете продолжить или начать с начала?",
            reply_markup=not_finished_markup
        )
    else:
        # Если нет не законченных тестов, вызываем функцию start_new_test()
        await start_new_test(user_id)

    # Закрываем соединение с базой данных
    conn.close()


# Обработчик для продолжения ранее начатого теста
@dp.callback_query_handler(lambda callback_query: callback_query.data.startswith('continue_test_'))
async def continue_test(callback_query: types.CallbackQuery, state: FSMContext):

    del messages_for_delete[:]
    user_id = callback_query.from_user.id
    test_id = callback_query.data.split('_')

    # Подключаемся к SQLite базе данных quiz.db
    conn = sqlite3.connect('quiz.db')
    cursor = conn.cursor()

    # Получаем из main_test id записи, где user_id = id текущего пользователя и status = pending
    cursor.execute("SELECT id FROM main_test WHERE user_id = ? AND status = 'pending'", (user_id,))
    pre_test_id = cursor.fetchone()

    test_id = pre_test_id[0]  # Извлекаем значение id

    await test_process(user_id, test_id)


# Обработчик для инициализации теста
@dp.callback_query_handler(lambda callback_query: callback_query.data == "start_new_test")
async def go_new_test(callback_query: types.CallbackQuery, state: FSMContext):

    del messages_for_delete[:]
    user_id = callback_query.from_user.id

    # Подключаемся к SQLite базе данных quiz.db
    conn = sqlite3.connect('quiz.db')
    cursor = conn.cursor()

    try:
        # Получаем из main_test id записи, где user_id = id текущего пользователя и status = pending
        cursor.execute("SELECT id FROM main_test WHERE user_id = ? AND status = 'pending'", (user_id,))
        test_id = cursor.fetchone()

        test_id = test_id[0]  # Извлекаем значение id

        if test_id:
            # Удаляем из main_test полученную запись
            cursor.execute("DELETE FROM main_test WHERE id = ?", (test_id,))
            conn.commit()  # Сохраняем изменения в базе данных

            # Удаляем из main_test_process все записи, где test_id = полученному ранее id
            cursor.execute("DELETE FROM main_test_process WHERE test_id_id = ?", (test_id,))
            conn.commit()  # Сохраняем изменения в базе данных

        # Отправляем пользователю сообщение о завершении теста
        # await bot.send_message(user_id, "Текущий тест был завершен.")

    except sqlite3.Error as e:
        print(f"Ошибка базы данных: {e}")
    finally:
        conn.close()  # Закрываем соединение с базой данных
        await start_new_test(user_id)


# Обработчик для инфоблока оформления подписки
@dp.callback_query_handler(lambda callback_query: callback_query.data == "subscribe")
async def go_new_subscribt(callback_query: types.CallbackQuery):

    go_new_subscribe_markup = types.InlineKeyboardMarkup()
    go_new_subscribe_markup.add(process_subscribe_button, cancel_button)

    await bot.send_message(callback_query.from_user.id, """<b>Подписка на 30 дней - 1000р.</b>\n\nОформив подписку, вы сможете:\n- Проходить тест на определение архетипа личности неограниченное количество раз\n- Приглашать неограниченное количество друзей для проверки совместимости""", reply_markup=go_new_subscribe_markup, parse_mode="HTML")


# Обработчик для инфоблока покупки одной совместимости
@dp.callback_query_handler(lambda callback_query: callback_query.data == "buy_compat")
async def go_new_compat(callback_query: types.CallbackQuery):

    go_new_compat_markup = types.InlineKeyboardMarkup()
    go_new_compat_markup.add(process_compat_button, cancel_button)

    await bot.send_message(callback_query.from_user.id, """<b>Одна проверка совместимости - 300р.</b>

    Позволяет проверить совместимость вашего архетипа и архетипа любого вашего друга.""", reply_markup=go_new_compat_markup, parse_mode="HTML")



# Обработчик для профиля пользователя
@dp.callback_query_handler(lambda callback_query: callback_query.data == "get_profile")
async def get_my_profile(callback_query: types.CallbackQuery):

    my_profile_markup = types.InlineKeyboardMarkup()
    my_profile_markup.add(my_subscribes_button, my_archetype_button)
    my_profile_markup.add(cancel_button)

    # Узнаем инфу об имени пользователя
    user_name = callback_query.from_user.username

    await bot.send_message(callback_query.from_user.id, f"""Добро пожаловать, <b>{user_name}</b>!

    Выберите пункт меню: """, reply_markup=my_profile_markup, parse_mode="HTML")


# Показываем пользователю его подписки
@dp.callback_query_handler(lambda callback_query: callback_query.data == "get_subscribes")
async def get_my_subscribes(callback_query: types.CallbackQuery):

    user_id = callback_query.from_user.id
    # Подключение к базе данных
    conn = sqlite3.connect('quiz.db')
    cursor = conn.cursor()

    # Проверка наличия не законченного теста для данного пользователя
    cursor.execute("SELECT * FROM main_subscribe WHERE user_id = ?", (user_id,))
    subscribes_row = cursor.fetchone()

    # Если подписки есть
    if subscribes_row:
        end_date = subscribes_row[4]

        my_subscribe_markup = types.InlineKeyboardMarkup()
        my_subscribe_markup.add(profile_button)


        await bot.send_message(callback_query.from_user.id, f"В настоящий момент у вас есть одна активная подписка. Истекает <b>{end_date}</b>", reply_markup=my_subscribe_markup, parse_mode="HTML")

    else:
        my_subscribe_markup = types.InlineKeyboardMarkup()
        my_subscribe_markup.add(subscribe_button, profile_button)


        await bot.send_message(callback_query.from_user.id, "В настоящий момент у вас нет активных подписок", reply_markup=my_subscribe_markup)


# Показываем пользователю его подписки
@dp.callback_query_handler(lambda callback_query: callback_query.data == "get_archetype")
async def get_my_subscribes(callback_query: types.CallbackQuery):

    user_id = callback_query.from_user.id
    # Подключение к базе данных
    conn = sqlite3.connect('quiz.db')
    cursor = conn.cursor()

    # Проверка наличия не законченного теста для данного пользователя
    cursor.execute("SELECT archetype_id FROM main_user WHERE user_id = ?", (user_id,))
    archetype_row = cursor.fetchone()

    # Если архетип есть
    if archetype_row[0]:

        # Получаем имя архетипа
        cursor.execute("SELECT archetype_name FROM main_archetype WHERE id = ?", (archetype_row[0],))
        archetype_name_row = cursor.fetchone()

        # Получаем описание архетипа
        cursor.execute("SELECT archetype_description FROM main_archetype WHERE id = ?", (archetype_row[0],))
        archetype_description_row = cursor.fetchone()

        my_archetype_markup = types.InlineKeyboardMarkup()
        my_archetype_markup.add(profile_button)


        await bot.send_message(callback_query.from_user.id, f"""Ваш архетип - <b>{archetype_name_row[0]}</b>

{archetype_description_row[0]}""", reply_markup=my_archetype_markup, parse_mode="HTML")

    else:
        my_subscribe_markup = types.InlineKeyboardMarkup()
        my_subscribe_markup.add(start_test_button, profile_button)


        await bot.send_message(callback_query.from_user.id, "Ваш архетип пока не определен. Пройдите тест для его получения.", reply_markup=my_subscribe_markup)


# Обработчик исключений
# @dp.errors_handler(exception=RetryAfter)
# async def exception_handler(update: types.Update, exception: exceptions.RetryAfter):
#     await bot.send_message(user_id, f'Бот заблокирован на 10 секунд из-за слишком большого количества запросов. Контент загрузится автоматически. Пожалуйста, подождите.')
#     await asyncio.sleep(10)
#     await send_question_and_answers(user_id, test_id, current_question, question_text, answers)
#     return True
    
    
@dp.errors_handler()
async def retry_after_handler(update: types.Update, exception: Exception):
    if isinstance(exception, RetryAfter):
        retry_after_time = exception.retry_after
        await bot.send_message(user_id, f'Бот заблокирован на {retry_after_time} секунд из-за слишком большого количества запросов. Контент загрузится автоматически. Пожалуйста, подождите.')
        await asyncio.sleep(retry_after_time)
        # await send_question_and_answers(user_id, test_id, current_question, question_text, answers)
        await dp.process_update(update)


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
