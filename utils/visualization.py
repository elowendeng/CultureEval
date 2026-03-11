# utils/visualization.py
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import os
from typing import Dict, List


# Set Chinese font for matplotlib
plt.rcParams['font.sans-serif'] = ['WenQuanYi Micro Hei', 'SimHei', 'DejaVu Sans Fallback', 'Microsoft YaHei']
plt.rcParams['axes.unicode_minus'] = False


def plot_results(all_results: Dict[str, List[dict]], output_dir: str):
    # Merge all results
    rows = []
    for model, results in all_results.items():
        for r in results:
            rows.append({**r, "model": model})
    df = pd.DataFrame(rows)
    # 1. Average score of each model in each dimension
    summary = df.groupby(['model', 'dimension'])['score'].mean().round(2).unstack()
    # bar chart
    plt.figure(figsize=(12, 6))
    summary.plot(kind='bar', width=0.8, colormap='Set2', edgecolor='black')
    plt.title('CultureEval Multi-model Comparison', fontsize=16, fontweight='bold')
    plt.ylabel('Average Score (1-5)')
    plt.xlabel('Model')
    plt.ylim(0, 5)
    plt.legend(title='Dimension')
    plt.xticks(rotation=0)
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    for i, (model, row) in enumerate(summary.iterrows()):
        for j, score in enumerate(row):
            plt.text(i + j*0.2 - 0.3, score + 0.05, str(score), ha='center', fontsize=9, fontweight='bold')
    plt.tight_layout()
    bar_path = os.path.join(output_dir, 'model_comparison.png')
    plt.savefig(bar_path, dpi=200, bbox_inches='tight')
    plt.close()
    print(f"The comparison chart has been saved.: {bar_path}")
    # 2. Heatmap
    plt.figure(figsize=(10, 6))
    sns.heatmap(summary, annot=True, cmap="YlGnBu", fmt=".2f", linewidths=.5, cbar_kws={'label': 'Average Score'})
    plt.title('Model × Dimension Score Heatmap')
    heat_path = os.path.join(output_dir, 'heatmap.png')
    plt.savefig(heat_path, dpi=200, bbox_inches='tight')
    plt.close()
    print(f"Heatmap saved: {heat_path}")
    # HTML report keeps Chinese characters, so no need to convert encoding
    html_report(df, summary, output_dir)

def html_report(df: pd.DataFrame, summary: pd.DataFrame, output_dir: str):
    timestamp = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M")
    best_model = summary.mean(axis=1).idxmax()
    best_score = summary.mean(axis=1).max()

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>CultureEval 评估报告</title>
        <style>
            body {{ font-family: 'Microsoft YaHei', sans-serif; margin: 40px; background: #f9f9f9; }}
            h1, h2 {{ color: #d4380d; }}
            .header {{ background: #fff2e8; padding: 20px; border-radius: 10px; text-align: center; }}
            .stats {{ display: flex; justify-content: space-around; margin: 20px 0; }}
            .stat {{ background: white; padding: 15px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); text-align: center; }}
            img {{ max-width: 100%; border-radius: 8px; margin: 20px 0; }}
            table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
            th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
            th {{ background: #fff2e8; }}
            .score-5 {{ background: #d4edda; }}
            .score-4 {{ background: #fff3cd; }}
            .score-3 {{ background: #f8d7da; }}
            .score-2 {{ background: #f1c0c0; }}
            .score-1 {{ background: #d6d8db; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>CultureEval 中国文化理解评估报告</h1>
            <p>生成时间: {timestamp} | 样本数: {len(df)}</p>
        </div>

        <div class="stats">
            <div class="stat">
                <h3>最佳模型</h3>
                <p style="font-size: 1.5em; color: #d4380d;"><strong>{best_model}</strong></p>
            </div>
            <div class="stat">
                <h3>平均得分</h3>
                <p style="font-size: 1.5em;"><strong>{best_score:.2f}</strong></p>
            </div>
        </div>

        <h2>模型对比图</h2>
        <img src="model_comparison.png">

        <h2>得分热力图</h2>
        <img src="heatmap.png">

        <h2>详细结果</h2>
        <table>
            <tr>
                <th>ID</th>
                <th>模型</th>
                <th>维度</th>
                <th>问题</th>
                <th>回答</th>
                <th>得分</th>
                <th>评语</th>
            </tr>
    """

    for _, row in df.iterrows():
        score_class = f"score-{row['score']}"
        answer = row['answer'].replace('\n', '<br>')
        html += f"""
            <tr class="{score_class}">
                <td>{row['id']}</td>
                <td>{row['model']}</td>
                <td>{row['dimension']}</td>
                <td>{row['question'][:50]}...</td>
                <td>{answer[:100]}...</td>
                <td><strong>{row['score']}</strong></td>
                <td>{row['explanation']}</td>
            </tr>
        """

    html += """
        </table>
    </body>
    </html>
    """

    path = os.path.join(output_dir, 'report.html')
    with open(path, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"HTML report generated: {path}")