

def is_fim_llm(llm):
    return hasattr(llm, "code_complete_v2")
