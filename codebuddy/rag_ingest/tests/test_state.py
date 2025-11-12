from rag_ingest.state import LLM_CLIENT


def test_llm_create():
    chat_completion = LLM_CLIENT.chat.completions.create(
        model='gpt4-o',
        stream=False,
        messages=[{
            "role": "user",
            "content": "Hello world"
        }],
    )
    print(chat_completion)
    print('done')
