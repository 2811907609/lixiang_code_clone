class Dummytokenizer:
    '''a dummpy tokenizer to help test model performance.'''

    def get_vocab(self):
        return {'a': 1000}

    def encode(self, text, **kwargs):
        return [0] * len(text)

    def convert_ids_to_tokens(self, ids, *args, **kwargs):
        if isinstance(ids, int):
            return 'a'
        return ['a'] * len(ids)

    def batch_decode(self, ids, *args, **kwargs):
        n = len(ids)
        return [self.convert_ids_to_tokens(ids[i], *args, **kwargs) for i in range(n)]

    def decode(self, ids, *args, **kwargs):
        return self.convert_ids_to_tokens(ids, *args, **kwargs)
