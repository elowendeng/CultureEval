# src/evaluator.py
try:
    from src.model_interface import MLLMInterface
    from src.data_loader import load_benchmark
except ImportError:
    from model_interface import MLLMInterface
    from data_loader import load_benchmark

from utils.judge import LLMJudge
from utils.visualization import plot_results
import os
from tqdm import tqdm
import json
from datetime import datetime
from typing import List, Dict, Any


class CultureEvaluator:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self._validate_config()
        self.judge = LLMJudge()
        self.all_results: Dict[str, List[Dict]] = {}

    def _validate_config(self):
        """Verify configuration integrity"""
        required_keys = ['models', 'judge', 'benchmark', 'output_dir', 'judge_prompt', 'dimensions']
        for key in required_keys:
            if key not in self.config:
                raise ValueError(f"Missing required config key: {key}")
        # Check the baseline data path
        benchmark_path = self.config['benchmark']['path']
        if not os.path.exists(benchmark_path):
            raise FileNotFoundError(f"Benchmark file not found: {benchmark_path}")

    def run(self):
        data = load_benchmark(self.config['benchmark']['path'])
        output_dir = self.config['output_dir']
        os.makedirs(output_dir, exist_ok=True)
        # Traverse all models
        for model_name, model_cfg in self.config['models'].items():
            print(f"\n{'=' * 60}")
            print(f"Model being evaluated: {model_name}")
            print(f"{'=' * 60}")
            try:
                model = MLLMInterface(model_cfg)
                results = []
                for item in tqdm(data, desc=f"Evaluating {model_name}", unit="sample"):
                    try:
                        # Ensure the image path exists
                        image_path = item['image_path']
                        if not os.path.exists(image_path):
                            print(f"Warning: Image file not found: {image_path}")
                            answer = f"[Image not found: {image_path}]"
                        else:
                            answer = model.predict(image_path, item['question'])
                    except Exception as e:
                        answer = f"[Predict Failed] {str(e)}"
                    judge_result = self.judge.judge(
                        question=item['question'],
                        answer=answer,
                        reference=item['reference'],
                        dimension=item['dimension']
                    )
                    result = {
                        "id": item['id'],
                        "dimension": item['dimension'],
                        "question": item['question'],
                        "answer": answer,
                        "reference": item['reference'],
                        "score": judge_result['score'],
                        "explanation": judge_result['explanation'],
                        "model": model_name
                    }
                    results.append(result)
                self.all_results[model_name] = results
            except Exception as e:
                print(f"Model {model_name} initialization failed: {str(e)}")
                continue
        # Save + Visualize
        self.save_results()
        plot_results(self.all_results, output_dir)

    def save_results(self):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = f"{self.config['output_dir']}/full_results_{timestamp}.json"
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(self.all_results, f, ensure_ascii=False, indent=2)
        print(f"\nThe complete results have been saved: {path}")