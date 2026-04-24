import requests
from bs4 import BeautifulSoup
import json, sys, os, time
from datetime import datetime

# 터미널 한글 깨짐 방지
try:
    sys.stdout.reconfigure(encoding='utf-8')
except:
    pass

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
        rank = item.select_one('.grade').text.strip() if item.select_one('.grade') else ''
        change = item.select_one('.gradeUpDown').text.strip() if item.select_one('.gradeUpDown') else ''
        title = item.select_one('.title a').text.strip() if item.select_one('.title a') else ''
        link = item.select_one('.info > a')
        href = link.get('href', '') if link else ''
        price_tag = item.select_one('.price')
        price = price_tag.text.strip().replace('원','').replace(',','').strip() if price_tag else '0'
        qty = item.select_one('.qty b').text.strip() if item.select_one('.qty b') else ''
        biz = '사업자 전용' if item.select_one('.setBuyTrueImgWrap') else '일반'
        img = item.select_one('img').get('src', '') if item.select_one('img') else ''
        results.append({'rank':rank,'change':change,'img':img,
                        'title':title,'price':price,'qty':qty,
                        'biz':biz,'url':f"https://domeggook.com{href}"})
    return results

def crawl_all():
    all_data = {}
    for key, label, url in CATEGORIES:
        print(f"크롤링 중: {label}...")
        try:
            all_data[key] = crawl_one(url)
        except:
            all_data[key] = []
        time.sleep(1)

    # 카테고리 합산 로직
    all_rank_map = { i['url']: i['rank'] for i in all_data['all'] if i['url'] }
    merged = []
    seen = set()
    cat_labels = {'cat01':'패션잡화/화장품', 'cat02':'의류/언더웨어', 'cat03':'출산/유아동/완구', 'cat04':'가구/생활/취미', 'cat05':'스포츠/건강/식품', 'cat06':'가전/휴대폰/산업'}
    for k in ['cat01','cat02','cat03','cat04','cat05','cat06']:
        for item in all_data[k]:
            if item['url'] not in seen:
                seen.add(item['url'])
                item['cat_label'] = cat_labels[k]
                item['all_rank'] = all_rank_map.get(item['url'], '')
                merged.append(item)
    all_data['merged'] = merged
    return all_data

if __name__ == "__main__":
    data = crawl_all()
    os.makedirs('data', exist_ok=True)
    today = datetime.now().strftime('%Y-%m-%d')
    
    # 데이터 저장
    with open(f'data/{today}.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        
    # 인덱스 파일 업데이트
    idx_path = 'data/index.json'
    dates = json.load(open(idx_path, 'r', encoding='utf-8')) if os.path.exists(idx_path) else []
    if today not in dates:
        dates.append(today)
        dates.sort(reverse=True)
        json.dump(dates, open(idx_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    print(f"✅ {today} 데이터 저장 완료")
