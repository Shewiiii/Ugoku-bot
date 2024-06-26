from datetime import datetime


class Timer:
    def __init__(self) -> None:
        self.t0 = datetime.now()
        self.t = self.t0

    def round(self) -> str:
        new = datetime.now()
        delta = new - self.t
        self.t = new
        return f'{delta.seconds}.{str(delta.microseconds)[:2]}s'
    
    def total(self) -> str:
        new = datetime.now()
        total_delta = new - self.t0
        return f'{total_delta.seconds}.{str(total_delta.microseconds)[:2]}s'
