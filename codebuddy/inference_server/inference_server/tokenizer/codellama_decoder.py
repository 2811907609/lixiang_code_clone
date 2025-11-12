SPIECE_UNDERLINE = "▁"


def codellama_decode(tokenizer, token_ids) -> str:
    '''
    CodeLlama decoder has bug that it will trim first whitespace. need to fix it here

        def convert_tokens_to_string(self, tokens):
        """Converts a sequence of tokens (string) in a single string."""
        # since we manually add the prefix space, we have to remove it when decoding
        if tokens[0].startswith(SPIECE_UNDERLINE):
            tokens[0] = tokens[0][1:]

    '''
    tokens = tokenizer.convert_ids_to_tokens(token_ids)
    if tokens and tokens[0].startswith(SPIECE_UNDERLINE):
        tokens = [SPIECE_UNDERLINE] + tokens
    return tokenizer.convert_tokens_to_string(tokens)
