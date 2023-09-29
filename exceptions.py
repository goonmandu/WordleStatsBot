class NumberOfAttemptsMismatchException(Exception):
    def __init__(self, expected, got):
        self.message = f"Expected {expected} tries, instead got {got}."

    def __str__(self):
        return self.message
