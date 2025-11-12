from inference_server.types import CompletionItem, PromptComposeInfo


def new_completion_item(text: str) -> CompletionItem:
    prefix, suffix = text.split('║')
    prompt = PromptComposeInfo(
        used_prefix=prefix,
        used_suffix=suffix,
    )
    return CompletionItem(prompt_info=prompt)


not_changed_symbol = object()


def run_testcases(testcases: list[tuple], fn):
    for name, input, output, expected in testcases:
        if expected == not_changed_symbol:
            expected = output
        item = new_completion_item(input)
        item.set_output(output)
        fn(item)
        assert item.output_text() == expected, name
