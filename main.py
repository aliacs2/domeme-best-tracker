import requests
from bs4 import BeautifulSoup
import json, sys, os, time
from datetime import datetime

# 기존 설정 유지
CATEGORIES = [
    ('all',   '전체 랭킹',        'https://domeggook.com/main/item/itemPopular.php?cat=01_00&login=pc'),
    ('cat01', '패션잡화/화장품',   'https://domeggook.com/main/item/itemPopular.php?cat=01_01'),
    ('cat02', '의류/언더웨어',     'https://domeggook.com/main/item/itemPopular.php?cat=01_02'),
    ('cat03', '출산/유아동/완구',   'https://domeggook.com/main/item/itemPopular.php?cat=01_03'),
    ('cat04', '가구/생활/취미',    'https://domeggook.com/main/item/itemPopular.php?cat=01_04'),
    ('cat05', '스포츠/건강/식품',  'https://domeggook.com/main/item/itemPopular.php?cat=01_05'),
    ('cat06', '가전/휴대폰/산업',  'https://domeggook.com/main/item/itemPopular.php?cat=01_06'),
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "ko-KR,ko;q=0.9",
    "Referer": "https://domeggook.com/",
}

def crawl_one(url):
    response = requests.get(url, headers=HEADERS, timeout=15)
    text = response.content.decode('euc-kr', errors='replace')
    soup = BeautifulSoup(text, 'html.parser')
    items = soup.select('#itemPopularsUl li')
    results = []
    for item in items:
        # (기존 크롤링 로직 동일)
        rank = item.select_one('.grade').text.strip() if item.select_one('.grade') else ''
        rank_change = item.select_one('.gradeUpDown').text.strip() if item.select_one('.gradeUpDown') else ''
        title = item.select_one('.title a').text.strip() if item.select_one('.title a') else ''
        href = item.select_one('.info > a').get('href', '') if item.select_one('.info > a') else ''
        full_url = f"https://domeggook.com{href}" if href else ''
        price_text = item.select_one('.price').text.strip().replace('원','').replace(',','').strip() if item.select_one('.price') else '0'
        qty = item.select_one('.qty b').text.strip() if item.select_one('.qty b') else ''
        is_biz = '사업자 전용' if item.select_one('.setBuyTrueImgWrap') else '일반'
        img_url = item.select_one('img').get('src', '') if item.select_one('img') else ''
        results.append({'rank':rank,'change':rank_change,'img':img_url, 'title':title,'price':price_text,'qty':qty, 'biz':is_biz,'url':full_url})
    return results

def crawl_all():
    all_data = {}
    for key, label, url in CATEGORIES:
        print(f"  크롤링 중: {label} ...")
        try:
            items = crawl_one(url)
            all_data[key] = items
        except:
            all_data[key] = []
        time.sleep(1)

    # 합산 로직 유지
    all_rank_map = { (i['url'] or i['title']): i['rank'] for i in all_data.get('all', []) if (i['url'] or i['title']) }
    seen_urls = set()
    merged = []
    CAT_KEYS = ['cat01','cat02','cat03','cat04','cat05','cat06']
    CAT_LABELS = {'cat01':'패션잡화/화장품', 'cat02':'의류/언더웨어', 'cat03':'출산/유아동/완구', 'cat04':'가구/생활/취미', 'cat05':'스포츠/건강/식품', 'cat06':'가전/휴대폰/산업'}
    
    for ck in CAT_KEYS:
        for item in all_data.get(ck, []):
            uid = item.get('url') or item.get('title')
            if uid in seen_urls: continue
            seen_urls.add(uid)
            item['cat_label'] = CAT_LABELS[ck]
            item['all_rank'] = all_rank_map.get(uid, '')
            merged.append(item)
    all_data['merged'] = merged
    return all_data

if __name__ == "__main__":
    print("도매꾹 데이터 수집 시작...")
    final_data = crawl_all()
    
    # [데일리 저장 로직 추가]
    os.makedirs('data', exist_ok=True)
    today = datetime.now().strftime('%Y-%m-%d')
    
    # 1. 오늘 날짜 JSON 저장
    with open(f'data/{today}.json', 'w', encoding='utf-8') as f:
        json.dump(final_list, f, ensure_ascii=False, indent=2)
        
    # 2. 날짜 목록 index.json 업데이트
    index_path = 'data/index.json'
    if os.path.exists(index_path):
        with open(index_path, 'r', encoding='utf-8') as f:
            date_list = json.load(f)
    else:
        date_list = []
    
    if today not in date_list:
        date_list.append(today)
        date_list.sort(reverse=True)
        with open(index_path, 'w', encoding='utf-8') as f:
            json.dump(date_list, f, ensure_ascii=False, indent=2)
            
    print(f"✅ {today} 데이터 저장 완료")
