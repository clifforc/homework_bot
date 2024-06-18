import logging
import os
import sys
import time
from http import HTTPStatus

import requests
from dotenv import load_dotenv
from telebot import TeleBot

import exceptions

load_dotenv()


PRACTICUM_TOKEN = os.getenv('TOKEN_YP')
TELEGRAM_TOKEN = os.getenv('TOKEN_TG')
TELEGRAM_CHAT_ID = os.getenv('MY_TG_ID')


RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


logging.basicConfig(
    level=logging.DEBUG,
    filename='program.log',
    filemode='w',
    format='%(asctime)s - %(levelname)s - %(message)s - %(name)s'
)


def check_tokens():
    """Функция проверяет доступность переменных окружения."""

    for key in (PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID):
        try:
            if not key:
                raise ValueError(
                    f'Токен {key} отсутствует! Проверь .evn файл.'
                )
        except ValueError as error:
            logging.critical(error)
            sys.exit()


def send_message(bot, message):
    """Функция отправляем сообщение в чат"""

    try:
        bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message
        )
    except Exception as error:
        logging.error(error)
        raise exceptions.MessageError(str(error))
    logging.debug(f'Сообщение: "{message}" отправлено!')


def get_api_answer(timestamp):
    """
    Функция выполняет GET-запрос к кэндпоинту API,
    чтобы получить статус домашнего задания.
    """

    try:
        response = requests.get(
            ENDPOINT, headers=HEADERS, params={'from_date': timestamp}
        )
    except requests.exceptions.RequestException as error:
        endpoint_error = exceptions.EndpointError(str(error))
        logging.error(endpoint_error)
        raise endpoint_error

    if response.status_code != HTTPStatus.OK:
        requests_error = requests.HTTPError(
            f'Запрос к API завершился с кодом ошибки: '
            f'{response.status_code}'
        )
        logging.error(requests_error)
        raise requests_error
    else:
        return response.json()


def check_response(response):
    """Проверяем получен ли ответ от API."""

    if not response:
        message = 'Ответ от API не получен'
        logging.error(message)
        print(message)
        return False
    if not isinstance(response, dict):
        message = 'Ответ от API не является словарём.'
        logging.error(TypeError(message))
        raise TypeError(message)
    if 'homeworks' not in response:
        message = 'Ключа "homeworks" нет в словаре.'
        logging.error(KeyError(message))
        raise KeyError(message)
    if not isinstance(response['homeworks'], list):
        message = 'Данные по ключу "homeworks" не являются списком.'
        logging.error(TypeError(message))
        raise TypeError(message)
    return True


def parse_status(homework):
    """Извлекаем из ответа API имя работы и статут ее проверки"""

    try:
        homework_name = homework['homework_name']
        status = homework['status']
        if status not in HOMEWORK_VERDICTS:
            message = f'Unknown status: {status}'
            logging.error(KeyError(message))
            raise KeyError(message)
        verdict = HOMEWORK_VERDICTS.get(status)
        message = (f'Изменился статус проверки работы '
                   f'"{homework_name}". {verdict}')
        logging.debug(message)
        return message
    except KeyError:
        message = 'Ключ "homework_name" отсутствует в словаре homework.'
        logging.error(KeyError(message))
        raise KeyError(message)


def days_to_seconds(days):
    """Функция для перевода дней в секунды."""

    return days * 24 * 60 * 60


def main():
    """Основная логика работы бота."""

    check_tokens()

    bot = TeleBot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time()) - days_to_seconds(2)

    last_status = None

    while True:
        try:
            response = get_api_answer(timestamp)

            if check_response(response):
                homeworks = response.get('homeworks', [])
                if not homeworks:
                    logging.debug(
                        'В ответе API получен пустой список домашних работ'
                    )
                    continue

                homework = homeworks[0]
                current_status = homework['status']

                if current_status != last_status:
                    message = parse_status(homework)
                    send_message(bot, message)
                    last_status = current_status
                else:
                    logging.debug('Статус проверки не изменился')

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(message)
            print(message)
            break

        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
