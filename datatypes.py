class NameAndAvg:
    def __init__(self, n, a, s):
        self.name = n
        self.average = a
        self.samples = s

    def __str__(self):
        return f"`{format(round(self.average, 2), '.2f')}` - {self.name} ({self.samples})"
