# utils/judge.py
import openai
import json
import yaml
from typing import Dict, Any
import re
import logging
import os

logger = logging.getLogger(__name__)


class LLMJudge:
    def __init__(self, config_path="configs/default.yaml"):
        with open(config_path, 'r', encoding='utf-8') as f:
            cfg = yaml.safe_load(f)['judge']
        self.client = openai.OpenAI(
            api_key=os.environ.get(cfg['api_key']),
            base_url=os.environ.get(cfg['base_url'])
        )
        self.model_name = cfg['model_name']

    def judge(self, question: str, answer: str, reference: str, dimension: str) -> Dict[str, Any]:
        prompt = """
你是一个中国文化专家。请评估以下模型输出是否准确、完整且文化敏感。
评分标准（1-5分）：
1: 完全错误或严重误解
2: 部分正确但有明显错误
3: 基本正确但不够深入
4: 准确且有文化洞察
5: 完美无缺，体现深厚文化理解

请以JSON格式输出结果，包含score和explanation两个字段。
""".strip()

        full_prompt = f"""
{prompt}

问题: {question}
模型回答: {answer}
参考答案: {reference}
评估维度: {dimension}
"""
        try:
            # Correct Alibaba Cloud text message format - use strings directly
            messages = [
                {
                    "role": "user",
                    "content": full_prompt  # Direct string, not an array
                }
            ]
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=0.2,
                max_tokens=512
            )
            raw = response.choices[0].message.content.strip()
            # Try parsing JSON
            try:
                result = json.loads(raw)
                if 'score' not in result or 'explanation' not in result:
                    raise ValueError("Missing required fields")
            except json.JSONDecodeError:
                # If it's not standard JSON, try extracting the score
                score_match = re.search(r'"score"\s*:\s*(\d+)', raw)
                if score_match:
                    score = int(score_match.group(1))
                else:
                    score_match = re.search(r"'score'\s*:\s*(\d+)", raw)
                    score = int(score_match.group(1)) if score_match else 3
                explanation_match = re.search(r'"explanation"\s*:\s*"([^"]+)"', raw)
                explanation = explanation_match.group(1) if explanation_match else "自动解析评分"
                result = {
                    "score": max(1, min(5, score)),
                    "explanation": explanation
                }
            return result
        except Exception as e:
            logger.error(f"Judge failed for dimension {dimension}: {str(e)}")
            return {"score": 3, "explanation": f"Evaluation system error: {str(e)[:100]}"}