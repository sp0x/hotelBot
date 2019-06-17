class Reply:

    def __init__(self, box, type, text):
        if isinstance(text, list) and not isinstance(text, str):
            text = '. '.join(text)
        data = box.data if box is not None else None
        self.type = type
        self.data = box.data if box is not None else None
        self.text = text
        self.img = data['img'] if (data is not None and 'img' in data) else None
        self.buttons = [] if box is None else box.buttons

    def str(self):
        text = self.text
        if isinstance(text, list) and not isinstance(text, str):
            text = '. '.join(text)
        return text

    def prepend(self, prefix):
        self.text = prefix + self.text

    def __str__(self) -> str:
        return self.text