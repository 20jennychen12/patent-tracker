import google.genai as genai
from google.genai import types
from pydantic import BaseModel
import asyncio
import json
import os
from typing import List, Dict, Any
from datetime import datetime

# ==========================================
# 配置区 (已优化)
# ==========================================
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

# 定义 Pydantic 模型
class PatentAnalysis(BaseModel):
    summary: str
    improvements: str
    assignee: str

# 我们使用经测试可用的 gemini-flash-latest 模型以确保稳定性
MODEL_NAME = 'gemini-flash-latest' 

# 高质量的专业化 System Prompt (针对结构胶粘剂优化)
SYSTEM_PROMPT = """
You are a distinguished Material Science expert specializing in Advanced Structural Adhesives (Epoxies, Polyurethanes, Acrylics, Cyanoacrylates).
Your audience consists of R&D directors and PhD researchers. Analyze the patent data and provide deep technical insights.

Extract the following in strictly structured JSON:
1. summary: Focus on the novel chemical composition, specific catalyst/hardener mechanisms, or unique substrate bonding techniques. (75-125 words, English)
2. improvements: Quantify the technical edge (e.g., % increase in T-peel strength, reduction in Tg, specific cure cycle optimization, or VOC reduction). (75-125 words, English)
3. assignee: Exact corporate name (translated to English if necessary).

TONE: Academic, rigorous, and data-driven. Avoid generic marketing language.
"""

async def analyze_single_patent(client: genai.Client, patent: Dict[str, Any]) -> Dict[str, Any]:
    """
    使用升级后的 Pro 模型分析单篇专利。
    """
    # 状态检查
    if patent.get("summary") and patent.get("summary") not in ["Failed to analyze", "Failed to provide summary", "AI summary currently unavailable"]:
        return patent
    
    patent_id = patent.get("patent_number", "unknown")
    title = patent.get("title", "")
    abstract = patent.get("abstract", "")
    
    user_input = f"""
    [Patent ID]: {patent_id}
    [Title]: {title}
    [Abstract]: {abstract}
    
    Analyze the technical novelty based on the abstract above. Provide insights on adhesive chemistry.
    """
    
    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=user_input,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                response_mime_type="application/json",
                response_schema=PatentAnalysis,
                temperature=0.1, # 降低随机性，保证严谨
            ),
        )
        
        analysis_result = json.loads(response.text)
        patent.update(analysis_result)
        print(f"✅ [Pro 分析完成]: {patent_id}")
        return patent
        
    except Exception as e:
        if any(err in str(e) for err in ["429", "RESOURCE_EXHAUSTED", "quota"]):
            raise e
            
        print(f"❌ 分析专利 {patent_id} 失败: {e}")
        patent.update({
            "summary": "AI summary currently unavailable (Technical error).",
            "improvements": "In-depth review pending.",
            "assignee": patent.get("assignee", "N/A")
        })
        return patent

async def process_patents_concurrently(patents_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    处理专利列表。针对 Pro 模型的 2 RPM 限制进行了优化。
    """
    if not GEMINI_API_KEY:
         print("⚠️ 错误: 未找到 API KEY。")
         return patents_list
         
    if not patents_list:
        return []

    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 启动 Pro 模型深度分析模式 (目标: {len(patents_list)} 篇)...")
    
    client = genai.Client(api_key=GEMINI_API_KEY)
    results = []
    
    for i, patent in enumerate(patents_list):
        p_id = patent.get("patent_number")
        print(f"[{i+1}/{len(patents_list)}] 正在深入分析: {p_id}...")
        
        retries = 3
        while retries > 0:
            try:
                analyzed_patent = await analyze_single_patent(client, patent)
                results.append(analyzed_patent)
                
                # 实时保存，防止中断
                os.makedirs("data", exist_ok=True)
                with open("data/patents.json", "w", encoding="utf-8") as f:
                    json.dump(results + patents_list[len(results):], f, indent=4, ensure_ascii=False)
                
                break 
            except Exception as core_err:
                retries -= 1
                if "429" in str(core_err) or "RESOURCE_EXHAUSTED" in str(core_err):
                    # Pro 模型免费版限制很严，如果触发限制需要等待较长时间
                    wait_time = 35 
                    print(f"⏳ 触发配额限制。正在等待 {wait_time} 秒后重试... (剩余尝试次数: {retries})")
                    await asyncio.sleep(wait_time)
                else:
                    print(f"Unexpected error: {core_err}")
                    results.append(patent)
                    break
        
        # 适度的等待时间确保不触发 15 RPM 限制
        if i < len(patents_list) - 1:
            await asyncio.sleep(5)
            
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 深度分析全部完成！")
    return results

            
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 所有专利分析完成！\n")
    return results

def run_ai_analysis(patents_list: List[Dict[str, Any]]):
    """
    提供给外部调用的同步入口函数。
    """
    # 巧妙地在普通同步函数中运行异步任务
    return asyncio.run(process_patents_concurrently(patents_list))

if __name__ == "__main__":
    # 为了测试，我们尝试读取之前 scraper.py 保存的原始数据
    try:
        with open("raw_patents.json", "r", encoding="utf-8") as f:
            sample_data = json.load(f)
            
        if sample_data:
            print(f"读取到 {len(sample_data)} 条测试数据。")
            # 截取前两项作为测试，防止无意消耗太多配额
            test_data = sample_data[:2] 
            
            # 运行测试
            analyzed_data = run_ai_analysis(test_data)
            
            print("\n--- 最终整合了 AI 分析的数据 ---")
            print(json.dumps(analyzed_data, indent=4, ensure_ascii=False))
            
            # 将最终结果保存
            with open("patents.json", "w", encoding="utf-8") as out:
                json.dump(analyzed_data, out, ensure_ascii=False, indent=4)
            print("测试结果已完整保存到 patents.json (可用于前端展示)")
            
    except FileNotFoundError:
         print("未找到 raw_patents.json。请先运行 scraper.py 生成带有数据的原始文件。")
