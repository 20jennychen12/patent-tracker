import json
from datetime import datetime
from scraper import get_recent_patents
from ai_analyzer import run_ai_analysis

def main():
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 启动专利追踪自动化流程...")
    
    # 第一步：获取最新专利数据
    raw_patents = get_recent_patents()
    
    if not raw_patents:
        print("本周没有找到新的专利数据，流程结束。")
        return
        
    print(f"成功获取到 {len(raw_patents)} 条原始专利数据，开始交给 AI 处理...")
    
    # 第二步：使用大模型并发提取核心信息
    analyzed_patents = run_ai_analysis(raw_patents)
    
    # 第三步：将最终结果覆盖写入 patents.json 供前端使用
    # 注意这里保存的文件名是 patents.json，而不是 raw_patents.json
    output_filename = "data/patents.json"
    import os
    os.makedirs("data", exist_ok=True)
    with open(output_filename, "w", encoding="utf-8") as f:
        json.dump(analyzed_patents, f, ensure_ascii=False, indent=4)
        
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 流程执行完毕。")
    print(f"✅ 所有带有 AI 解析结果的数据已成功保存至 {output_filename}")

if __name__ == "__main__":
    main()
