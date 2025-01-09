# Project:      Agent
# Author:       yomu
# Time:         2025/01/08
# Version:      0.1
# Description:  agent prompt optimizer template

"""
    PromptOptimizer_template
"""

from langchain.prompts import PromptTemplate


# 检查错别字的prompt
check_typographical_errors_prompt = PromptTemplate(
    input_variables=["text"],
    template=f"""你的任务是对以下用尖括号<>括起来的文本进行以下步骤:
                步骤:
                    1. 检查文本是否含有错别字
                    2. 如果有错别字，则将其修改正确
                    3. 检查文本是否有逻辑错误
                    4. 如果有逻辑错误，请修改文本以使得文本的逻辑正确
                    5. 检查文本是否语句通顺
                    6. 如果语句不通顺，请修改文本使得语句通顺

                注意事项:
                    1. 如果文本中有代码，请不要修改代码及其注释
                    2. 请不要修改文本本来想表达的意思
                    3. 如果执行以上步骤时与注意事项的第二条相违背，则以注意事项为准
                    4. 你只能返回一个字符串
                    5. 不要返回思考和步骤的过程
                    6. 不要返回任何说明
                    7. 即使文本没有错误，也必须按照格式返回

                返回结果的格式:
                    "修改后的文本"

                文本: <{{text}}>
        """
)

# 优化的prompt
optimize_prompt = PromptTemplate(
    input_variables=[],
    template=f""
)

# 