class MockedObject:
    def __init__(self, mocked_obj):
        self.__mocked_obj = mocked_obj
    def noop(*args, **kwargs): pass
    def __getattr__(self, _):
        attr_value = getattr(self.__mocked_obj, _)
        if callable(attr_value):
            return self.noop
        else:
            return None