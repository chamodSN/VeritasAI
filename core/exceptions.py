#Base exception for all VeritasAI errors
class VeritasAIError(Exception):

    http_status: int = 500
    message: str = "An internal error occurred"

    def __init__(self, message: str | None = None):
        self.message = message or self.__class__.message
        super().__init__(self.message)