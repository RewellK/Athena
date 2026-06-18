from learning.day_memory_buffer import DayMemoryBuffer


class DailyLearningJournal:
    def __init__(self, buffer=None):
        self.buffer = buffer or DayMemoryBuffer()

    def record(self, content, **kwargs):
        return self.buffer.add_entry(content, **kwargs)

    def summary(self):
        return self.buffer.summary()
