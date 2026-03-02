import requests
import json
import os
from datetime import datetime, timedelta

# 配置区
# 你需要去 https://serpapi.com/ 免费注册一个账号，获取API Key (每月100次免费额度)
SERPAPI_KEY = os.environ.get("SERPAPI_KEY", "")
SEARCH_QUERIES = [
    "epoxy adhesive",
    "polyurethane adhesive",
    "battery adhesive",
    "automotive adhesive",
    "structural adhesive"
]

def get_recent_patents():
    """
    使用 SerpApi (Google Patents) 搜索过去一周关于 'structural adhesive' 的专利
    """
    if SERPAPI_KEY == "YOUR_SERPAPI_KEY_HERE":
         print("⚠️ 警告: 请使用你自己的 SERPAPI_KEY 替换默认值或设置环境变量。")

    # SerpApi Google Patents 接口的 URL
    api_url = "https://serpapi.com/search.json"
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 开始获取多种胶水分类的最新专利数据...")
    
    extracted_patents = []

    # Get date roughly one year ago
    one_year_ago = datetime.now() - timedelta(days=365)
    date_str = one_year_ago.strftime("%Y%m%d")

    for query in SEARCH_QUERIES:
        print(f"正在检索: {query} ...")
        # 构建请求参数
        # engine: google_patents
        # q: 搜索词
        # after: 限制在此日期之后公布的专利 (格式: YYYYMMDD)
        params = {
            "engine": "google_patents",
            "q": f'"{query}"',
            "after": f"publication:{date_str}",
            "api_key": SERPAPI_KEY,
        }
        
        try:
            # 添加超时设置防止网络挂起
            response = requests.get(api_url, params=params, timeout=15)
            response.raise_for_status() # 检查 HTTP 状态码是否正常
            data = response.json()
        except requests.exceptions.RequestException as e:
            print(f"❌ 网络请求异常 ({query}): {e}")
            continue
        except json.JSONDecodeError as e:
            print(f"❌ JSON 解析失败 ({query}): {e}")
            continue

        if "error" in data:
            print(f"❌ SerpApi 报错 ({query}): {data['error']}")
            continue

        results = data.get("organic_results", [])
        if not results:
            print(f"ℹ️ {query} 未查找到相关专利数据。")
            continue

        # 因为有多个关键词，我们需要把关键词作为一个标签(category)存进字典
        for item in results:
            try:
                # 去重判定：如果同一个专利在不同的搜索词下出现，我们不重复添加
                patent_number = item.get("patent_id", "Unknown ID")
                if any(p.get('patent_number') == patent_number for p in extracted_patents):
                    continue
                
                title = item.get("title", "No Title")
                assignee = item.get("assignee", "Unknown Assignee")
                abstract = item.get("snippet", "No abstract available.") 
                url = item.get("link", "")
                
                pub_date_str = item.get("publication_date")
                if pub_date_str:
                    try:
                        datetime.strptime(pub_date_str, "%Y-%m-%d")
                    except ValueError:
                        pass
                else:
                    pub_date_str = "Unknown Date"

                patent_info = {
                    "patent_number": patent_number,
                    "title": title,
                    "publication_date": pub_date_str,
                    "assignee": assignee,
                    "abstract": abstract,
                    "url": url,
                    "category": query # 记录它属于哪个类别
                }
                extracted_patents.append(patent_info)
                
            except Exception as e:
                print(f"⚠️ 解析某条专利记录时出错, 已跳过: {e}")
                continue

    print(f"✅ 成功获取 {len(extracted_patents)} 条有效专利。\n")
    return extracted_patents

if __name__ == "__main__":
    # 运行测试
    patents_list = get_recent_patents()
    
    # 打印前2个结果检查一下
    if patents_list:
        print("--- 示例数据格式 ---")
        print(json.dumps(patents_list[:2], indent=4, ensure_ascii=False))
        
        # 暂时将结果保存到本地，供下一步（AI总结）使用
        with open("raw_patents.json", "w", encoding="utf-8") as f:
            json.dump(patents_list, f, ensure_ascii=False, indent=4)
        print("已将原始数据保存至 raw_patents.json")
