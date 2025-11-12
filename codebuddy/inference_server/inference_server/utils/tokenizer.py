import random


def gen_random_prompt(tokenizer, length):
    result = ''
    vocabs = list(tokenizer.get_vocab().keys())
    for _ in range(0, length):
        random_index = random.randint(0, len(vocabs) - 1)
        result += vocabs[random_index]
    return result
