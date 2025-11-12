import random

default_words_list = [
    '\t', '.', 'a', 'apple', 'banana', 'cherry', 'date', 'elderberry', 'fig',
    'grape', 'honeydew'
]


def generate_random_text(total_chars, total_lines, words_list=None):
    if not words_list:
        words_list = default_words_list

    if total_chars < total_lines:
        raise ValueError(
            "Total characters must be at least equal to total lines for this approach."
        )

    result = []
    total_chars_excluding_newlines = total_chars - (total_lines - 1)
    chars_per_line = total_chars_excluding_newlines // total_lines  # Average characters per line
    extra_chars = total_chars_excluding_newlines % total_lines  # Extra characters to distribute

    for i in range(total_lines):
        line_length = chars_per_line + (1 if i < extra_chars else 0
                                       )  # Distribute extra characters
        line = ''

        while len(line) < line_length:
            remaining_space = line_length - len(line)
            # Select a word randomly
            word = random.choice(words_list)
            # If the selected word fits the remaining space accounting for space or if it is the first word in the line
            if len(word) <= remaining_space and (line or
                                                 len(word) == remaining_space):
                if line and len(line) + len(
                        word
                ) + 1 <= line_length:  # Add a space before the word if not the first word
                    line += ' '
                line += word
            else:
                # Fill remaining space with spaces (to ensure we have exact number of total characters)
                line += ' ' * remaining_space
                break

        result.append(line)

    return '\n'.join(result)
