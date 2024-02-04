class NameAndAvg:
    def __init__(self, n, a, s, u):
        self.name = n
        self.average = a
        self.samples = s
        self.unsolved = u
        self.solved = s - u

    def __str__(self):
        return f"`{format(round(self.average, 2), '.2f')}` - {self.name} "\
               f"({self.solved}/{self.samples} : {round(self.solved * 100 / self.samples, 2)}%)"

    def avgstr(self):
        return f"{format(round(self.average, 2), '.2f')}"

    def namestr(self):
        return self.name

    def fracstr(self):
        return f"{self.solved}/{self.samples}"

    def pctstr(self):
        return f"{format(round(self.solved * 100 / self.samples, 2), '.2f')}%"


class PathAndCreationTime:
    def __init__(self, path, created_at):
        self.path = path
        self.created_at = created_at

    def __str__(self):
        return f"{self.path}, {self.created_at}"