class EndpointError(Exception):
    """Не удалось получить ответ на запрос к энпоинту API."""
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)


class MessageError(Exception):
    """Не удалось отправить сообщение."""
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)
