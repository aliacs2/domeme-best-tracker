import requests
from bs4 import BeautifulSoup
import json
import os
import time
from datetime import datetime


def crawl_dome_category(cat_id, cat_name):
    url = f"https://domeggook.com/main/item/itemPopular.php?cat={cat_id}&login=pc"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        # 도매꾹 특유의 한글 깨짐 방지
        text = response.content.decode('euc-kr', errors='replace')
        soup = BeautifulSoup(text, 'html.parser')
        items = soup.select('#itemPopularsUl li')

        results = []
        for item in items:
            title_tag = item.select_one('.title a')
            if not title_tag: continue

            title = title_tag.text.strip()
            href = title_tag.get('href', '')
            item_id = href.split('?')[0].replace('/', '')

            price_tag = item.select_one('.price')
            price = price_tag.text.strip().replace('원', '').replace(',', '').strip() if price_tag else '0'

            img_tag = item.select_one('img')
            img_url = img_tag.get('src', '') if img_tag else ''

            rank_tag = item.select_one('.grade')
            rank = rank_tag.text.strip() if rank_tag else ''

            results.append({
                'category_name': cat_name,
                'rank': rank,
                'id': item_id,
                'title': title,
                'price': int(price) if price.isdigit() else 0,
                'img': img_url,
                'url': f"https://domeggook.com/{item_id}"
            })
        return results
    except Exception as e:
        print(f"[{cat_name}] 에러: {e}")
        return []


def main():
    cat_list = {
        "01_00": "전체 베스트", "01_01": "가전/디지털", "01_02": "의류/패션",
        "01_03": "잡화/뷰티", "01_04": "식품/생활", "01_05": "가구/홈데코", "01_06": "스포츠/건강"
    }

    raw_data = []
    for cid, cname in cat_list.items():
        print(f"{cname} 수집 중...")
        raw_data.extend(crawl_dome_category(cid, cname))
        time.sleep(1.5)

    # 중복 분석 (여러 카테고리에 걸쳐 있는 상품 찾기)
    item_map = {}
    for item in raw_data:
        iid = item['id']
        if iid not in item_map:
            item_map[iid] = item
            item_map[iid]['all_cats'] = []
        if item['category_name'] not in item_map[iid]['all_cats']:
            item_map[iid]['all_cats'].append(item['category_name'])

    final_list = []
    for iid, item in item_map.items():
        item['is_multi_cat'] = len(item['all_cats']) > 1
        item['is_overall_best'] = "전체 베스트" in item['all_cats']
        final_list.append(item)

    # 파일 저장 (data 폴더)
    os.makedirs('data', exist_ok=True)
    today = datetime.now().strftime('%Y-%m-%d')

    # 1. 오늘 데이터 저장
    with open(f'data/{today}.json', 'w', encoding='utf-8') as f:
        json.dump(final_list, f, ensure_ascii=False, indent=2)

    # 2. 날짜 인덱스 업데이트
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


if __name__ == "__main__":
    main()