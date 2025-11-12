import pytest

from ai_agents.modules.feishuproject.create_item import parse_items_from_text, create_sr_item


def test_parse_items_from_text_normal_case():
    """测试正常输入情况"""
    input_text = '''
    SR：构建全文投机编辑性能评测集
    AR：性能评测方案
    AR：性能评测数据集生产（可以复用模型训练数据集） P0
    '''

    result = parse_items_from_text(input_text)
    print(f'result.....{result}')


@pytest.mark.asyncio
async def test_create_sr():
    await create_sr_item('hello4')


# def test_agent_create_sr_and_ars():
#     text = '''
# SR: 生成高质量种子数据
# AR：基于vcos仓库依赖解析抽取测试用例与其对应测试步骤
# AR: 基于llm-as-judge筛选高质量数据作为种子数据集
# '''
#     code_agent.run(text)
