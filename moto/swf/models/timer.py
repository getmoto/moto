from moto.core import BaseModel


class Timer(BaseModel):
    def __init__(self, background_timer, started_event_id):
        self.background_timer = background_timer
        self.started_event_id = started_event_id

    def start(self):
        return self.background_timer.start()

    def is_alive(self):
        return self.background_timer.is_alive()

    def cancel(self):
        return self.background_timer.cancel()
