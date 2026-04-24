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
        rank       = item.select_one('.grade').text.strip() if item.select_one('.grade') else ''
        rank_change= item.select_one('.gradeUpDown').text.strip() if item.select_one('.gradeUpDown') else ''
        title      = item.select_one('.title a').text.strip() if item.select_one('.title a') else ''
        link       = item.select_one('.info > a')
        href       = link.get('href', '') if link else ''
        full_url   = f"https://domeggook.com{href}" if href else ''
        price      = item.select_one('.price')
        price_text = price.text.strip().replace('원','').replace(',','').strip() if price else '0'
        qty        = item.select_one('.qty b').text.strip() if item.select_one('.qty b') else ''
        biz_only   = item.select_one('.setBuyTrueImgWrap')
        is_biz     = '사업자 전용' if biz_only else '일반'
        img        = item.select_one('img').get('src', '') if item.select_one('img') else ''
        results.append({'rank':rank,'change':rank_change,'img':img_url if (img_url := img) else '',
                        'title':title,'price':price_text,'qty':qty,
                        'biz':is_biz,'url':full_url})
    return results

def crawl_all():
    all_data = {}
    for key, label, url in CATEGORIES:
        print(f"  크롤링 중: {label} ...")
        all_data[key] = crawl_one(url)
        time.sleep(1)

    all_rank_map = { (i['url'] or i['title']): i['rank'] for i in all_data['all'] if (i['url'] or i['title']) }
    merged = []
    seen = set()
    cat_labels = {'cat01':'패션잡화/화장품', 'cat02':'의류/언더웨어', 'cat03':'출산/유아동/완구', 'cat04':'가구/생활/취미', 'cat05':'스포츠/건강/식품', 'cat06':'가전/휴대폰/산업'}
    for ck in ['cat01','cat02','cat03','cat04','cat05','cat06']:
        for item in all_data[ck]:
            uid = item['url'] or item['title']
            if uid not in seen:
                seen.add(uid)
                item['cat_label'] = cat_labels[ck]
                item['all_rank'] = all_rank_map.get(uid, '')
                merged.append(item)
    all_data['merged'] = merged
    return all_data

if __name__ == "__main__":
    print("도매꾹 데이터 수집 시작...")
    final_data = crawl_all()
    
    os.makedirs('data', exist_ok=True)
    today = datetime.now().strftime('%Y-%m-%d')
    
    # 1. 오늘 데이터 저장
    with open(f'data/{today}.json', 'w', encoding='utf-8') as f:
        json.dump(final_data, f, ensure_ascii=False, indent=2)
        
    # 2. 인덱스 업데이트
    idx_p = 'data/index.json'
    dates = json.load(open(idx_p, 'r', encoding='utf-8')) if os.path.exists(idx_p) else []
    if today not in dates:
        dates.append(today)
        dates.sort(reverse=True)
        json.dump(dates, open(idx_p, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    print(f"✅ {today} 저장 완료")
