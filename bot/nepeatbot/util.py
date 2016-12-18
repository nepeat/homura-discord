class Dummy(object):
    def blank_fn(self, *args, **kwargs):
        pass

    def __getattr__(self, attr):
        return self.blank_fn

    def __setattr__(self, attr, val):
        pass
