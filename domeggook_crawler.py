import requests
from bs4 import BeautifulSoup
import json, sys, os, time
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')

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

# 데이터 저장 디렉토리
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')


def crawl_one(url):
    response = requests.get(url, headers=HEADERS, timeout=15)
    text = response.content.decode('euc-kr', errors='replace')
    soup = BeautifulSoup(text, 'html.parser')
    items = soup.select('#itemPopularsUl li')
    results = []
    for item in items:
        rank       = item.select_one('.grade')
        rank       = rank.text.strip() if rank else ''
        rank_change= item.select_one('.gradeUpDown')
        rank_change= rank_change.text.strip() if rank_change else ''
        title      = item.select_one('.title a')
        title      = title.text.strip() if title else ''
        link       = item.select_one('.info > a')
        href       = link.get('href', '') if link else ''
        full_url   = f"https://domeggook.com{href}" if href else ''
        price      = item.select_one('.price')
        price_text = price.text.strip().replace('원','').replace(',','').strip() if price else '0'
        qty        = item.select_one('.qty b')
        qty        = qty.text.strip() if qty else ''
        biz_only   = item.select_one('.setBuyTrueImgWrap')
        is_biz     = '사업자 전용' if biz_only else '일반'
        img        = item.select_one('img')
        img_url    = img.get('src', '') if img else ''
        results.append({'rank':rank,'change':rank_change,'img':img_url,
                        'title':title,'price':price_text,'qty':qty,
                        'biz':is_biz,'url':full_url})
    return results


def crawl_all():
    all_data = {}
    for key, label, url in CATEGORIES:
        print(f"  크롤링 중: {label} ...", end=' ')
        try:
            items = crawl_one(url)
            all_data[key] = items
            print(f"{len(items)}개")
        except Exception as e:
            print(f"실패 ({e})")
            all_data[key] = []
        time.sleep(0.5)

    # 6개 카테고리 합산 탭 (중복 URL 제거, 출처 카테고리 정보 포함)
    CAT_KEYS = ['cat01','cat02','cat03','cat04','cat05','cat06']
    CAT_LABELS = {
        'cat01':'패션잡화/화장품', 'cat02':'의류/언더웨어',
        'cat03':'출산/유아동/완구', 'cat04':'가구/생활/취미',
        'cat05':'스포츠/건강/식품', 'cat06':'가전/휴대폰/산업',
    }
    all_rank_map = {}
    for item in all_data.get('all', []):
        uid = item.get('url') or item.get('title')
        if uid:
            all_rank_map[uid] = item.get('rank', '')

    seen_urls = set()
    merged = []
    for ck in CAT_KEYS:
        for item in all_data.get(ck, []):
            uid = item.get('url') or item.get('title')
            if uid in seen_urls:
                continue
            seen_urls.add(uid)
            all_rank = all_rank_map.get(uid, '')
            merged.append({**item, 'cat_label': CAT_LABELS[ck], 'all_rank': all_rank})
    all_data['merged'] = merged
    print(f"  카테고리 합산: {len(merged)}개 (중복 제거)")
    return all_data


def save_json(all_data, date_str):
    """날짜별 JSON 파일로 저장"""
    os.makedirs(DATA_DIR, exist_ok=True)
    json_path = os.path.join(DATA_DIR, f'ranking_{date_str}.json')
    payload = {
        'date': date_str,
        'crawled_at': datetime.now().isoformat(),
        'data': all_data
    }
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False)
    print(f"✅ JSON 저장: {json_path}")
    return json_path


def get_available_dates():
    """저장된 날짜 목록 반환 (최신순)"""
    if not os.path.exists(DATA_DIR):
        return []
    dates = []
    for fname in os.listdir(DATA_DIR):
        if fname.startswith('ranking_') and fname.endswith('.json'):
            date_str = fname.replace('ranking_', '').replace('.json', '')
            dates.append(date_str)
    return sorted(dates, reverse=True)


def make_controls_html(cat_key):
    return f"""
  <div class="controls">
    <div class="ctrl-group">
      <label>상품명 검색</label>
      <input type="text" id="search-{cat_key}" placeholder="검색어 입력..." oninput="render('{cat_key}')">
    </div>
    <div class="ctrl-group">
      <label>가격 범위 (원)</label>
      <div class="price-range">
        <input type="number" id="priceMin-{cat_key}" placeholder="최소" min="0" oninput="render('{cat_key}')">
        <span>~</span>
        <input type="number" id="priceMax-{cat_key}" placeholder="최대" min="0" oninput="render('{cat_key}')">
      </div>
    </div>
    <div class="ctrl-group">
      <label>구분 필터</label>
      <select id="biz-{cat_key}" onchange="render('{cat_key}')">
        <option value="">전체</option>
        <option value="일반">일반</option>
        <option value="사업자 전용">사업자 전용</option>
      </select>
    </div>
    <div class="ctrl-group">
      <label>하이라이트만 보기</label>
      <select id="hl-{cat_key}" onchange="render('{cat_key}')">
        <option value="">전체</option>
        <option value="new">신규 진입</option>
        <option value="up">급상승 (▲3 이상)</option>
        <option value="both">신규 + 급상승</option>
      </select>
    </div>
    <div class="ctrl-group sort-ctrl">
      <label>정렬 기준</label>
      <select id="sort-{cat_key}" onchange="sortBySelect('{cat_key}', this.value)">
        <option value="rankNum_1">순위 오름차순</option>
        <option value="priceNum_1">가격 낮은순</option>
        <option value="priceNum_-1">가격 높은순</option>
        <option value="changeNum_-1">변동 상승순</option>
        <option value="title_1">상품명 가나다순</option>
      </select>
    </div>
    <button class="btn-reset" onclick="resetAll('{cat_key}')">↺ 초기화</button>
  </div>
  <div class="legend">
    <span>하이라이트:</span>
    <div class="legend-item"><div class="legend-dot dot-new"></div>신규 진입</div>
    <div class="legend-item"><div class="legend-dot dot-up"></div>급상승 ▲3↑</div>
  </div>
  <p class="count-label" id="count-{cat_key}"></p>
  <div class="table-wrap">
    <table>
      <thead><tr>
        <th class="col-bm">북마크</th>
        <th class="col-rank  sortable asc" id="th-{cat_key}-rankNum"   onclick="sortBy('{cat_key}','rankNum')">순위<span class="sort-icon"></span></th>
        <th class="col-img">이미지</th>
        <th class="col-change sortable"    id="th-{cat_key}-changeNum" onclick="sortBy('{cat_key}','changeNum')">변동<span class="sort-icon"></span></th>
        <th class="col-title  sortable"    id="th-{cat_key}-title"     onclick="sortBy('{cat_key}','title')">상품명<span class="sort-icon"></span></th>
        <th class="col-price  sortable"    id="th-{cat_key}-priceNum"  onclick="sortBy('{cat_key}','priceNum')">가격<span class="sort-icon"></span></th>
        <th class="col-qty">최소수량</th>
      </tr></thead>
      <tbody id="body-{cat_key}"></tbody>
    </table>
  </div>
  <div class="card-list" id="cards-{cat_key}"></div>"""


def save_html(all_data, available_dates, today_str, filename='domeggook_ranking.html'):
    json_str = json.dumps(all_data, ensure_ascii=False)

    # 날짜별 JSON 데이터 목록 (HTML에 임베드)
    dates_json = json.dumps(available_dates, ensure_ascii=False)

    js_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'js_template.js')
    with open(js_path, 'r', encoding='utf-8') as f:
        js = f.read()
    js = js.replace('__ALL_DATA__', json_str)

    # 탭 버튼 생성
    tab_btns = ''
    for key, label, _ in CATEGORIES:
        active = 'active' if key == 'all' else ''
        tab_btns += f'<button class="tab-btn {active}" id="tab-{key}" onclick="switchTab(\'{key}\')">{label}</button>\n  '
    tab_btns += '<button class="tab-btn" id="tab-merged" onclick="switchTab(\'merged\')">🗂 카테고리 합산</button>\n  '
    tab_btns += '<button class="tab-btn" id="tab-bm" onclick="switchTab(\'bm\')">🔖 북마크 <span id="bmBadge"></span></button>'

    # 카테고리 뷰 생성
    cat_views = ''
    for key, label, _ in CATEGORIES:
        display = '' if key == 'all' else 'style="display:none"'
        cat_views += f'<div id="view-{key}" {display}>\n{make_controls_html(key)}\n</div>\n\n'

    # merged 탭 뷰
    merged_view = f'<div id="view-merged" style="display:none">\n{make_controls_html("merged")}\n</div>\n'

    # 날짜 히스토리 패널 HTML
    date_options = '\n'.join(
        f'<option value="{d}" {"selected" if d == today_str else ""}>{format_date_label(d)}</option>'
        for d in available_dates
    )

    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>도매꾹 인기 랭킹</title>
<style>
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ font-family: 'Malgun Gothic', sans-serif; background: #f3f4f6; padding: 20px; color: #111; }}
h1 {{ font-size: 20px; font-weight: 700; margin-bottom: 6px; }}

/* ── 날짜 선택 바 ── */
.date-bar {{
  background: #fff; border-radius: 12px; padding: 12px 18px;
  margin-bottom: 14px; box-shadow: 0 1px 3px rgba(0,0,0,.07);
  display: flex; align-items: center; gap: 12px; flex-wrap: wrap;
}}
.date-bar label {{ font-size: 12px; color: #888; font-weight: 600; white-space: nowrap; }}
.date-select {{
  padding: 6px 10px; border: 1px solid #e5e7eb; border-radius: 7px;
  font-size: 13px; background: #fff; font-family: inherit; outline: none;
  cursor: pointer; color: #111; min-width: 180px;
}}
.date-select:focus {{ border-color: #6366f1; }}
.date-info {{ font-size: 12px; color: #6366f1; font-weight: 600; }}
.date-badge {{
  display: inline-block; background: #ede9fe; color: #4f46e5;
  padding: 3px 10px; border-radius: 20px; font-size: 11px; font-weight: 700;
}}
.date-count {{ font-size: 11px; color: #aaa; }}

/* ── 탭 ── */
.tab-bar {{ display: flex; flex-wrap: wrap; gap: 4px; margin-bottom: 14px; }}
.tab-btn {{
  padding: 7px 14px; border: 1px solid #e5e7eb; border-radius: 8px;
  font-size: 12px; font-family: inherit; background: #fff;
  cursor: pointer; color: #555; white-space: nowrap; transition: all .12s;
}}
.tab-btn.active {{ background: #4f46e5; color: #fff; border-color: #4f46e5; font-weight: 600; }}
.tab-btn:hover:not(.active) {{ background: #f0f0ff; border-color: #c7d2fe; color: #4f46e5; }}

/* ── 컨트롤 ── */
.controls {{ background: #fff; border-radius: 12px; padding: 14px 18px; margin-bottom: 10px; box-shadow: 0 1px 3px rgba(0,0,0,.07); display: flex; flex-wrap: wrap; gap: 14px; align-items: flex-end; }}
.ctrl-group {{ display: flex; flex-direction: column; gap: 4px; }}
.ctrl-group label {{ font-size: 11px; color: #888; font-weight: 600; }}
.ctrl-group input[type=text] {{ padding: 6px 10px; border: 1px solid #e5e7eb; border-radius: 7px; font-size: 13px; width: 180px; font-family: inherit; outline: none; }}
.ctrl-group input[type=text]:focus {{ border-color: #6366f1; }}
.ctrl-group input[type=number] {{ padding: 6px 8px; border: 1px solid #e5e7eb; border-radius: 7px; font-size: 13px; width: 90px; font-family: inherit; outline: none; }}
.ctrl-group input[type=number]:focus {{ border-color: #6366f1; }}
.price-range {{ display: flex; gap: 5px; align-items: center; }}
.price-range span {{ font-size: 12px; color: #bbb; }}
.ctrl-group select {{ padding: 6px 8px; border: 1px solid #e5e7eb; border-radius: 7px; font-size: 13px; background: #fff; font-family: inherit; outline: none; cursor: pointer; }}
.btn-reset {{ padding: 6px 14px; border: 1px solid #e5e7eb; border-radius: 7px; font-size: 12px; background: #fff; cursor: pointer; color: #555; font-family: inherit; }}
.btn-reset:hover {{ background: #f3f4f6; }}

/* ── 범례 ── */
.legend {{ display: flex; gap: 12px; margin-bottom: 8px; align-items: center; font-size: 12px; color: #666; }}
.legend-item {{ display: flex; align-items: center; gap: 4px; }}
.legend-dot {{ width: 11px; height: 11px; border-radius: 3px; }}
.dot-new {{ background: #fde68a; border: 1px solid #f59e0b; }}
.dot-up  {{ background: #bbf7d0; border: 1px solid #22c55e; }}
.count-label {{ font-size: 12px; color: #888; margin-bottom: 7px; }}

/* ── 테이블 ── */
.table-wrap {{ background: #fff; border-radius: 12px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,.07); }}
table {{ width: 100%; border-collapse: collapse; font-size: 13px; table-layout: fixed; }}
thead {{ background: #f9fafb; }}
th {{ padding: 10px 8px; font-size: 11px; color: #888; font-weight: 600; border-bottom: 1px solid #e5e7eb; white-space: nowrap; letter-spacing: .3px; }}
th.sortable {{ cursor: pointer; user-select: none; }}
th.sortable:hover {{ background: #f0f0ff; color: #4f46e5; }}
th.asc  .sort-icon::after {{ content: ' ▲'; color: #4f46e5; font-size: 9px; }}
th.desc .sort-icon::after {{ content: ' ▼'; color: #4f46e5; font-size: 9px; }}
th:not(.asc):not(.desc) .sort-icon::after {{ content: ' ⇅'; color: #ccc; font-size: 9px; }}
td {{ padding: 8px; border-bottom: 1px solid #f3f4f6; vertical-align: middle; }}
tbody tr:last-child td {{ border-bottom: none; }}
tbody tr:hover td {{ background: #fafafa !important; }}
tr.hl-new td {{ background: #fffbeb; }}
tr.hl-up  td {{ background: #f0fdf4; }}
tr.hl-new td:first-child {{ border-left: 3px solid #f59e0b; }}
tr.hl-up  td:first-child {{ border-left: 3px solid #22c55e; }}

.col-bm    {{ width: 44px; text-align: center; }}
.col-rank  {{ width: 50px; text-align: center; }}
.col-img   {{ width: 200px; text-align: center; }}
.col-change{{ width: 60px; text-align: center; }}
.col-title {{ min-width: 0; }}
.col-price {{ width: 88px; text-align: right; white-space: nowrap; }}
.col-qty   {{ width: 70px; text-align: center; }}

.rank-num {{ font-weight: 700; font-size: 15px; }}
.chg-up   {{ color: #16a34a; font-size: 12px; font-weight: 700; }}
.chg-down {{ color: #dc2626; font-size: 12px; font-weight: 700; }}
.chg-flat {{ color: #bbb; font-size: 12px; }}
.badge-new {{ display: inline-block; background: #fde68a; color: #92400e; padding: 2px 6px; border-radius: 5px; font-size: 11px; font-weight: 700; border: 1px solid #f59e0b; }}
.badge-biz {{ display: inline-block; background: #fff7ed; color: #9a3412; padding: 1px 5px; border-radius: 4px; font-size: 10px; margin-left: 4px; border: 1px solid #fed7aa; vertical-align: middle; }}
.cat-tag   {{ display: inline-block; font-size: 10px; color: #6366f1; background: #ede9fe; border-radius: 3px; padding: 1px 5px; margin-top: 2px; }}
.all-rank-sub {{ font-size: 10px; color: #bbb; margin-top: 2px; letter-spacing: -0.2px; }}
.thumb {{ width: 192px; height: 192px; object-fit: cover; border-radius: 7px; border: 1px solid #e5e7eb; display: block; margin: auto; }}
.title-link {{ color: #111; text-decoration: none; font-size: 12px; line-height: 1.5; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }}
.title-link:hover {{ color: #4f46e5; text-decoration: underline; }}
.price-val {{ font-weight: 700; }}
.qty-val {{ font-size: 11px; color: #999; }}
.no-result {{ text-align: center; padding: 50px; color: #bbb; font-size: 14px; }}

/* ── 북마크 ── */
.bm-btn {{ background: none; border: none; cursor: pointer; font-size: 20px; line-height: 1; padding: 2px; transition: transform .15s; }}
.bm-btn:hover {{ transform: scale(1.2); }}
.bm-btn.on  {{ color: #f59e0b; }}
.bm-btn.off {{ color: #ddd; }}
.bm-fname {{ font-size: 9px; color: #888; margin-top: 2px; line-height: 1.2; }}
.folder-bar {{ background: #fff; border-radius: 12px; padding: 14px 18px; margin-bottom: 10px; box-shadow: 0 1px 3px rgba(0,0,0,.07); }}
.folder-bar-top {{ display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px; }}
.folder-bar-top span {{ font-size: 14px; font-weight: 600; }}
.btn-new-folder {{ padding: 5px 12px; border: 1px dashed #c7d2fe; border-radius: 20px; font-size: 12px; background: #f0f0ff; color: #4f46e5; cursor: pointer; font-family: inherit; }}
.btn-bm-io {{ padding: 5px 12px; border-radius: 20px; font-size: 12px; cursor: pointer; font-family: inherit; border: 1px solid; transition: all .12s; }}
.btn-export {{ background: #f0fdf4; color: #16a34a; border-color: #bbf7d0; }}
.btn-export:hover {{ background: #dcfce7; border-color: #86efac; }}
.btn-import {{ background: #eff6ff; color: #2563eb; border-color: #bfdbfe; }}
.btn-import:hover {{ background: #dbeafe; border-color: #93c5fd; }}
.folder-chips {{ display: flex; flex-wrap: wrap; gap: 6px; }}
.chip {{ display: flex; align-items: center; gap: 4px; padding: 5px 10px; border-radius: 20px; font-size: 12px; cursor: pointer; border: 1px solid #e5e7eb; background: #f9fafb; color: #555; user-select: none; }}
.chip.active {{ background: #4f46e5; color: #fff; border-color: #4f46e5; }}
.chip:hover:not(.active) {{ background: #f0f0ff; border-color: #c7d2fe; color: #4f46e5; }}
.chip-cnt {{ font-size: 10px; background: rgba(0,0,0,.1); border-radius: 10px; padding: 1px 5px; }}
.chip.active .chip-cnt {{ background: rgba(255,255,255,.3); }}
.chip-del {{ font-size: 11px; opacity: .5; margin-left: 2px; }}
.chip-del:hover {{ opacity: 1; color: #dc2626; }}
.chip-latest::after {{ content: ' ★'; font-size: 10px; }}

/* ── 팝업 ── */
.popup-overlay {{ display: none; position: fixed; inset: 0; z-index: 199; }}
.popup {{ display: none; position: fixed; z-index: 200; background: #fff; border: 1px solid #e5e7eb; border-radius: 10px; box-shadow: 0 8px 24px rgba(0,0,0,.14); width: 250px; padding: 14px; }}
.popup.open {{ display: block; }}
.popup h3 {{ font-size: 13px; font-weight: 600; margin-bottom: 10px; }}
.popup-folders {{ display: flex; flex-direction: column; gap: 4px; max-height: 160px; overflow-y: auto; margin-bottom: 8px; }}
.pf-row {{ display: flex; align-items: center; justify-content: space-between; padding: 6px 10px; border-radius: 6px; cursor: pointer; border: 1px solid #f0f0f0; transition: all .1s; }}
.pf-row:hover {{ background: #f0f0ff; border-color: #c7d2fe; }}
.pf-row.sel {{ background: #4f46e5; color: #fff; border-color: #4f46e5; }}
.pf-row.sel .pf-cnt {{ background: rgba(255,255,255,.3); }}
.pf-row.latest .pf-name::after {{ content: ' ★'; font-size: 10px; }}
.pf-name {{ font-size: 12px; font-weight: 500; }}
.pf-cnt {{ font-size: 10px; background: #f3f4f6; border-radius: 10px; padding: 1px 6px; color: #888; }}
.popup-divider {{ border: none; border-top: 1px solid #f0f0f0; margin: 8px 0; }}
.popup-new {{ display: flex; gap: 6px; margin-bottom: 8px; }}
.popup-new input {{ flex: 1; padding: 6px 8px; border: 1px solid #e5e7eb; border-radius: 6px; font-size: 12px; font-family: inherit; outline: none; }}
.popup-new input:focus {{ border-color: #6366f1; }}
.popup-new button {{ padding: 6px 10px; background: #4f46e5; color: #fff; border: none; border-radius: 6px; font-size: 12px; cursor: pointer; font-family: inherit; }}
.popup-confirm {{ width: 100%; padding: 7px; background: #4f46e5; color: #fff; border: none; border-radius: 7px; font-size: 13px; font-weight: 600; cursor: pointer; font-family: inherit; }}
.popup-confirm:hover {{ background: #4338ca; }}

/* ── 로딩 ── */
.loading-overlay {{
  display: none; position: fixed; inset: 0; z-index: 300;
  background: rgba(255,255,255,0.85); align-items: center; justify-content: center;
  flex-direction: column; gap: 12px;
}}
.loading-overlay.show {{ display: flex; }}
.spinner {{
  width: 40px; height: 40px; border: 4px solid #e5e7eb;
  border-top-color: #4f46e5; border-radius: 50%;
  animation: spin 0.8s linear infinite;
}}
@keyframes spin {{ to {{ transform: rotate(360deg); }} }}
.loading-text {{ font-size: 14px; color: #555; }}

/* ── 카드 레이아웃 (모바일 전용) ── */
.card-list {{ display: none; flex-direction: column; gap: 10px; }}
.card {{
  background: #fff; border-radius: 12px; overflow: hidden;
  box-shadow: 0 1px 4px rgba(0,0,0,.08);
  display: flex; gap: 0;
}}
.card.hl-new {{ border-left: 4px solid #f59e0b; background: #fffbeb; }}
.card.hl-up  {{ border-left: 4px solid #22c55e; background: #f0fdf4; }}
.card-img-wrap {{
  flex-shrink: 0; width: 110px; position: relative;
}}
.card-img-wrap img {{
  width: 110px; height: 110px; object-fit: cover; display: block;
}}
.card-img-wrap .card-rank {{
  position: absolute; top: 6px; left: 6px;
  background: rgba(0,0,0,.65); color: #fff;
  font-size: 13px; font-weight: 700;
  padding: 2px 7px; border-radius: 20px; line-height: 1.4;
}}
.card-img-wrap .card-bm {{
  position: absolute; top: 4px; right: 4px;
  background: none; border: none; cursor: pointer;
  font-size: 22px; line-height: 1; padding: 2px;
  filter: drop-shadow(0 1px 2px rgba(0,0,0,.4));
}}
.card-img-wrap .card-bm.on  {{ color: #f59e0b; }}
.card-img-wrap .card-bm.off {{ color: rgba(255,255,255,.85); }}
.card-body {{
  flex: 1; padding: 10px 12px; min-width: 0;
  display: flex; flex-direction: column; justify-content: space-between;
}}
.card-title {{
  font-size: 13px; line-height: 1.5; color: #111;
  text-decoration: none;
  display: -webkit-box; -webkit-line-clamp: 3;
  -webkit-box-orient: vertical; overflow: hidden;
  margin-bottom: 8px;
}}
.card-title:hover {{ color: #4f46e5; }}
.card-meta {{
  display: flex; align-items: center; gap: 6px; flex-wrap: wrap;
}}
.card-price {{
  font-size: 15px; font-weight: 700; color: #111;
}}
.card-change {{
  font-size: 12px; font-weight: 700;
}}
.card-qty {{
  font-size: 11px; color: #aaa;
}}
.card-tags {{
  display: flex; gap: 4px; flex-wrap: wrap; margin-top: 5px;
}}

/* ── 다크모드 ── */
body.dark {{ background: #111; color: #e5e7eb; }}
body.dark .date-bar,
body.dark .controls,
body.dark .folder-bar,
body.dark .table-wrap,
body.dark .card {{ background: #1e1e2e; box-shadow: 0 1px 4px rgba(0,0,0,.4); }}
body.dark .tab-btn {{ background: #1e1e2e; border-color: #374151; color: #9ca3af; }}
body.dark .tab-btn.active {{ background: #4f46e5; color: #fff; border-color: #4f46e5; }}
body.dark .tab-btn:hover:not(.active) {{ background: #2d2d3f; border-color: #6366f1; color: #a5b4fc; }}
body.dark thead {{ background: #16162a; }}
body.dark th {{ color: #6b7280; border-bottom-color: #374151; }}
body.dark td {{ border-bottom-color: #1f2937; }}
body.dark tbody tr:hover td {{ background: #1a1a2e !important; }}
body.dark tr.hl-new td {{ background: #2d2510; }}
body.dark tr.hl-up  td {{ background: #0f2a1a; }}
body.dark tr.hl-new td:first-child {{ border-left-color: #f59e0b; }}
body.dark tr.hl-up  td:first-child  {{ border-left-color: #22c55e; }}
body.dark .card.hl-new {{ background: #2d2510; }}
body.dark .card.hl-up  {{ background: #0f2a1a; }}
body.dark .ctrl-group label {{ color: #6b7280; }}
body.dark .ctrl-group input,
body.dark .ctrl-group select,
body.dark .btn-reset {{ background: #2d2d3f; border-color: #374151; color: #e5e7eb; }}
body.dark .ctrl-group input::placeholder {{ color: #4b5563; }}
body.dark .title-link,
body.dark .card-title {{ color: #e5e7eb; }}
body.dark .title-link:hover,
body.dark .card-title:hover {{ color: #a5b4fc; }}
body.dark .count-label,
body.dark .legend {{ color: #6b7280; }}
body.dark .chip {{ background: #2d2d3f; border-color: #374151; color: #9ca3af; }}
body.dark .chip.active {{ background: #4f46e5; color: #fff; border-color: #4f46e5; }}
body.dark .popup {{ background: #1e1e2e; border-color: #374151; }}
body.dark .pf-row {{ border-color: #374151; color: #e5e7eb; }}
body.dark .pf-row:hover {{ background: #2d2d3f; border-color: #6366f1; }}
body.dark .popup-new input {{ background: #2d2d3f; border-color: #374151; color: #e5e7eb; }}
body.dark .loading-overlay {{ background: rgba(17,17,17,0.9); }}
body.dark .loading-text {{ color: #9ca3af; }}
body.dark .date-badge {{ background: #2d2d3f; color: #a5b4fc; }}
body.dark .card-price {{ color: #e5e7eb; }}
body.dark .no-result {{ color: #4b5563; }}

/* 다크모드 토글 버튼 */
.dark-toggle {{
  margin-left: auto; background: none; border: 1px solid #e5e7eb;
  border-radius: 20px; padding: 4px 12px; font-size: 12px;
  cursor: pointer; color: #555; font-family: inherit;
  transition: all .15s; white-space: nowrap;
}}
.dark-toggle:hover {{ background: #f3f4f6; }}
body.dark .dark-toggle {{ border-color: #374151; color: #9ca3af; background: #1e1e2e; }}
body.dark .dark-toggle:hover {{ background: #2d2d3f; }}

/* ── 모바일 반응형 ── */
@media (max-width: 640px) {{
  body {{ padding: 12px 10px; }}
  h1 {{ font-size: 17px; }}

  /* 날짜바 */
  .date-bar {{ padding: 10px 12px; gap: 8px; }}
  .date-select {{ min-width: 0; flex: 1; font-size: 13px; }}
  .date-count {{ display: none; }}

  /* 탭 */
  .tab-bar {{ gap: 3px; }}
  .tab-btn {{ padding: 6px 10px; font-size: 11px; }}

  /* 컨트롤 */
  .controls {{ padding: 10px 12px; gap: 10px; }}
  .ctrl-group input[type=text] {{ width: 100%; }}
  .ctrl-group input[type=number] {{ width: 80px; }}

  /* 테이블 숨기고 카드 표시 */
  .table-wrap {{ display: none; }}
  .card-list {{ display: flex; }}

  /* 북마크 폴더바 */
  .folder-bar {{ padding: 10px 12px; }}
  .btn-bm-io {{ padding: 4px 8px; font-size: 11px; }}
}}
</style>
</head>
<body>

<!-- 로딩 오버레이 -->
<div class="loading-overlay" id="loadingOverlay">
  <div class="spinner"></div>
  <div class="loading-text">데이터 불러오는 중...</div>
</div>

<div style="display:flex;align-items:center;margin-bottom:10px;">
  <h1 style="margin-bottom:0;">도매꾹 인기 랭킹</h1>
  <button class="dark-toggle" id="darkToggle" onclick="toggleDark()">🌙 다크모드</button>
</div>

<!-- 날짜 선택 바 -->
<div class="date-bar">
  <label>📅 날짜 선택</label>
  <select class="date-select" id="dateSelect" onchange="loadDateData(this.value)">
    {date_options}
  </select>
  <span class="date-info" id="dateInfo"></span>
  <span class="date-count" id="dateCount">{len(available_dates)}개 날짜 저장됨</span>
</div>

<div class="tab-bar">
  {tab_btns}
</div>

{cat_views}
{merged_view}
<!-- 북마크 뷰 -->
<div id="view-bm" style="display:none">
  <div class="folder-bar">
    <div class="folder-bar-top">
      <span>폴더</span>
      <div style="display:flex;gap:6px;align-items:center">
        <button class="btn-new-folder" onclick="promptNewFolder()">+ 새 폴더</button>
        <button class="btn-bm-io btn-export" onclick="exportBookmarks()" title="북마크를 JSON 파일로 저장">💾 저장</button>
        <button class="btn-bm-io btn-import" onclick="importBookmarks()" title="JSON 파일에서 북마크 불러오기">📂 불러오기</button>
      </div>
    </div>
    <div class="folder-chips" id="folderChips"></div>
  </div>
  <p class="count-label" id="bmCountLabel"></p>
  <div class="table-wrap">
    <table>
      <thead><tr>
        <th class="col-bm">북마크</th>
        <th class="col-rank  sortable asc" id="th-bm-rankNum"   onclick="sortByBm('rankNum')">순위<span class="sort-icon"></span></th>
        <th class="col-img">이미지</th>
        <th class="col-change sortable"    id="th-bm-changeNum" onclick="sortByBm('changeNum')">변동<span class="sort-icon"></span></th>
        <th class="col-title  sortable"    id="th-bm-title"     onclick="sortByBm('title')">상품명<span class="sort-icon"></span></th>
        <th class="col-price  sortable"    id="th-bm-priceNum"  onclick="sortByBm('priceNum')">가격<span class="sort-icon"></span></th>
        <th class="col-qty">최소수량</th>
      </tr></thead>
      <tbody id="bmBody"></tbody>
    </table>
  </div>
  <div class="card-list" id="cards-bm"></div>
</div>

<!-- 팝업 -->
<div class="popup-overlay" id="popOverlay" onclick="closePopup()"></div>
<div class="popup" id="popup">
  <h3>📁 폴더 선택</h3>
  <div class="popup-folders" id="popFolderList"></div>
  <hr class="popup-divider">
  <div class="popup-new">
    <input type="text" id="popNewInput" placeholder="새 폴더 이름..." maxlength="20"
           onkeydown="if(event.key==='Enter') popCreateFolder()">
    <button onclick="popCreateFolder()">추가</button>
  </div>
  <hr class="popup-divider">
  <button class="popup-confirm" onclick="confirmBM()">저장</button>
</div>

<script>
// ══════════════════════════════════════════
//  날짜별 데이터 관리
// ══════════════════════════════════════════
const AVAILABLE_DATES = {dates_json};
const TODAY_STR = '{today_str}';

// 현재 표시 중인 데이터 (초기값: 오늘 데이터)
let ALL_DATA = {json_str};

function formatDateLabel(d) {{
  // YYYYMMDD -> YYYY-MM-DD
  return d.replace(/^(\\d{{4}})(\\d{{2}})(\\d{{2}})$/, '$1-$2-$3');
}}

function updateDateInfo(dateStr) {{
  const info = document.getElementById('dateInfo');
  if (!info) return;
  if (dateStr === TODAY_STR) {{
    info.innerHTML = '<span class="date-badge">오늘</span>';
  }} else {{
    const d = formatDateLabel(dateStr);
    info.innerHTML = `<span class="date-badge">📆 ${{d}}</span>`;
  }}
}}

async function loadDateData(dateStr) {{
  if (!dateStr) return;
  if (dateStr === TODAY_STR) {{
    // 오늘 데이터는 이미 임베드됨
    ALL_DATA = {json_str};
    rebuildData();
    renderCurrentTab();
    updateDateInfo(dateStr);
    return;
  }}
  // 다른 날짜는 JSON 파일 fetch
  const overlay = document.getElementById('loadingOverlay');
  overlay.classList.add('show');
  try {{
    const res = await fetch(`data/ranking_${{dateStr}}.json`);
    if (!res.ok) throw new Error('파일 없음');
    const payload = await res.json();
    ALL_DATA = payload.data;
    rebuildData();
    renderCurrentTab();
    updateDateInfo(dateStr);
  }} catch(e) {{
    alert(`${{formatDateLabel(dateStr)}} 데이터를 불러올 수 없습니다.\\n(${{e.message}})`);
    // 원래 날짜로 복원
    document.getElementById('dateSelect').value = TODAY_STR;
    updateDateInfo(TODAY_STR);
  }} finally {{
    overlay.classList.remove('show');
  }}
}}

// ══════════════════════════════════════════
//  초기화
// ══════════════════════════════════════════
{js}

// 날짜 info 초기 설정
updateDateInfo(TODAY_STR);
</script>
</body>
</html>"""

    with open(filename, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"✅ {filename} 저장 완료")


def format_date_label(d):
    """YYYYMMDD -> YYYY-MM-DD"""
    if len(d) == 8:
        return f"{d[:4]}-{d[4:6]}-{d[6:]}"
    return d


if __name__ == "__main__":
    today_str = datetime.now().strftime('%Y%m%d')
    print(f"도매꾹 카테고리별 랭킹 크롤링 시작... ({today_str})")

    all_data = crawl_all()
    total = sum(len(v) for v in all_data.values())
    print(f"총 {total}개 상품 크롤링 완료")

    # 날짜별 JSON 저장
    save_json(all_data, today_str)

    # 사용 가능한 날짜 목록 조회
    available_dates = get_available_dates()
    print(f"저장된 날짜: {available_dates}")

    # HTML 생성
    save_html(all_data, available_dates, today_str)
