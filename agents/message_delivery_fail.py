class MessageDeliveryFail(Exception):
    def __init__(self):
        super().__init__("Failed to deliver message")
