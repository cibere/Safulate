class EOF(Exception):
    def __init__(self):
        super().__init__("End of file reached")
