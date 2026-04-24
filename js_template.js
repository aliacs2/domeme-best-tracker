// ── 데이터 (Python이 주입) ──

// ── 카테고리 정의 ──
const CATEGORIES = [
  { key: 'all',   label: '📋 전체 랭킹' },
  { key: 'cat01', label: '패션잡화/화장품' },
  { key: 'cat02', label: '의류/언더웨어' },
  { key: 'cat03', label: '출산/유아동/완구' },
  { key: 'cat04', label: '가구/생활/취미' },
  { key: 'cat05', label: '스포츠/건강/식품' },
  { key: 'cat06', label: '가전/휴대폰/산업' },
  { key: 'merged', label: '🗂 카테고리 합산' },
  { key: 'bm',    label: '🔖 북마크' },
];

function parseChange(c) {
  if (!c || c === '-') return 0;
  if (c === 'NEW') return 9999;
  const m = c.match(/([▲▼])\s*(\d+)/);
  if (!m) return 0;
  return m[1] === '▲' ? parseInt(m[2]) : -parseInt(m[2]);
}

const DATA = {};

// ── rebuildData: ALL_DATA 변경 후 DATA 재구성 ──

// ══════════════════════════════════════════
//  다크모드
// ══════════════════════════════════════════
function toggleDark() {
  const isDark = document.body.classList.toggle('dark');
  localStorage.setItem('darkMode', isDark ? '1' : '0');
  document.getElementById('darkToggle').textContent = isDark ? '☀️ 라이트모드' : '🌙 다크모드';
}

(function() {
  const saved = localStorage.getItem('darkMode');
  if (saved === '1') {
    document.body.classList.add('dark');
    document.addEventListener('DOMContentLoaded', () => {
      const btn = document.getElementById('darkToggle');
      if (btn) btn.textContent = '☀️ 라이트모드';
    });
  }
})();

function rebuildData() {
  Object.keys(ALL_DATA).forEach(key => {
    DATA[key] = ALL_DATA[key].map(d => ({
      ...d,
      rankNum:   parseInt(d.rank)  || 0,
      priceNum:  parseInt(d.price) || 0,
      changeNum: parseChange(d.change),
      isNew:   d.change === 'NEW',
      isHotUp: parseChange(d.change) >= 3 && d.change !== 'NEW',
      cat_label: d.cat_label || '',
      all_rank:  d.all_rank  || '',
    }));
  });
}

// 초기 데이터 구성
rebuildData();

// ══════════════════════════════════════════
//  API 설정 (시놀로지)
// ══════════════════════════════════════════
const LS_DARK = 'darkMode';
const LS_API_URL = 'dmk_api_url';
const LS_API_KEY = 'dmk_api_key';

function getApiUrl() { return localStorage.getItem(LS_API_URL) || ''; }
function getApiKey() { return localStorage.getItem(LS_API_KEY) || ''; }

// ── 인메모리 북마크 상태 ──
let _BM = {};   // { url: folderId }
let _FL = [];   // [{ id, name, t }]

const loadBM = () => _BM;
const loadFL = () => _FL;
const saveBM = v => { _BM = v; syncToServer(); };
const saveFL = v => { _FL = v; syncToServer(); };
const itemKey = d => d.url || d.title;
const latestFid = () => { if(!_FL.length) return null; return [..._FL].sort((a,b)=>b.t-a.t)[0].id; };

function ensureDefaultFolder() {
  if (!_FL.length) { _FL = [{id:'f0', name:'기본 폴더', t:Date.now()}]; syncToServer(); }
}

// ══════════════════════════════════════════
//  서버 동기화
// ══════════════════════════════════════════
let _syncTimer = null;

// 저장 (디바운스 500ms)
function syncToServer() {
  clearTimeout(_syncTimer);
  _syncTimer = setTimeout(_doSync, 500);
}

async function _doSync() {
  const url = getApiUrl();
  const key = getApiKey();
  if (!url || !key) return;

  const seen = new Set();
  const items = [];
  Object.keys(DATA).forEach(catKey => {
    (DATA[catKey] || []).forEach(d => {
      const k = itemKey(d);
      if (!_BM[k] || seen.has(k)) return;
      seen.add(k);
      const folder = _FL.find(f => f.id === _BM[k]);
      items.push({
        folder_id: _BM[k], folder_name: folder ? folder.name : '(삭제된 폴더)',
        rank: d.rank, change: d.change, title: d.title, price: d.price,
        qty: d.qty, biz: d.biz, url: d.url, img: d.img,
        category: CATEGORIES.find(c=>c.key===catKey)?.label || catKey,
      });
    });
  });

  const payload = { version: 1, folders: _FL, bookmarks: _BM, items };
  try {
    await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-Secret-Key': key },
      body: JSON.stringify(payload),
    });
  } catch(e) { console.warn('북마크 동기화 실패:', e); }
}

// 불러오기
async function loadFromServer() {
  const url = getApiUrl();
  const key = getApiKey();
  if (!url || !key) return false;
  try {
    const res = await fetch(url, { headers: { 'X-Secret-Key': key } });
    if (!res.ok) return false;
    const data = await res.json();
    _BM = data.bookmarks || {};
    _FL = data.folders   || [];
    ensureDefaultFolder();
    return true;
  } catch(e) {
    console.warn('북마크 불러오기 실패:', e);
    return false;
  }
}

// ══════════════════════════════════════════
//  API 설정 UI
// ══════════════════════════════════════════
function openApiSettings() {
  const url = getApiUrl();
  const key = getApiKey();
  const modal = document.getElementById('apiModal');
  document.getElementById('apiUrlInput').value = url;
  document.getElementById('apiKeyInput').value = key;
  modal.style.display = 'flex';
}

function closeApiSettings() {
  document.getElementById('apiModal').style.display = 'none';
}

function updateApiSettingsBtnState() {
  const btn = document.getElementById('apiSettingsBtn');
  if (!btn) return;
  const connected = !!(getApiUrl() && getApiKey());
  btn.classList.toggle('connected', connected);
  btn.textContent = connected ? '🔗 서버 연결됨' : '🔗 서버 설정';
}

async function saveApiSettings() {
  const url = document.getElementById('apiUrlInput').value.trim();
  const key = document.getElementById('apiKeyInput').value.trim();
  if (!url || !key) { alert('URL과 키를 모두 입력하세요.'); return; }
  localStorage.setItem(LS_API_URL, url);
  localStorage.setItem(LS_API_KEY, key);
  closeApiSettings();
  showToast('⏳ 서버에서 북마크 불러오는 중...');
  const ok = await loadFromServer();
  if (ok) {
    renderCurrentTab(); renderBmFolderBar(); updateBmBadge();
    showToast(`✅ 연결 성공 — 북마크 ${Object.keys(_BM).length}개 불러옴`);
  } else {
    showToast('❌ 연결 실패 — URL과 키를 확인하세요');
  }
}

// ══════════════════════════════════════════
//  북마크 파일 저장 / 불러오기
// ══════════════════════════════════════════

// 저장: bookmarks_YYYYMMDD_HHMMSS.json 으로 다운로드
function exportBookmarks() {
  const bm = loadBM();
  const fl = loadFL();
  if (!Object.keys(bm).length) { alert('저장된 북마크가 없습니다.'); return; }

  // 북마크에 상품 상세 정보도 함께 저장
  const seen = new Set();
  const items = [];
  Object.keys(DATA).forEach(catKey => {
    DATA[catKey].forEach(d => {
      const key = itemKey(d);
      if (!bm[key] || seen.has(key)) return;
      seen.add(key);
      const folder = fl.find(f => f.id === bm[key]);
      items.push({
        folder_id:   bm[key],
        folder_name: folder ? folder.name : '(삭제된 폴더)',
        rank:    d.rank,
        change:  d.change,
        title:   d.title,
        price:   d.price,
        qty:     d.qty,
        biz:     d.biz,
        url:     d.url,
        img:     d.img,
        category: CATEGORIES.find(c=>c.key===catKey)?.label || catKey,
      });
    });
  });

  const payload = {
    exported_at: new Date().toISOString(),
    version: 1,
    folders: fl,
    bookmarks: bm,
    items: items,
  };

  const json   = JSON.stringify(payload, null, 2);
  const blob   = new Blob([json], { type: 'application/json' });
  const url    = URL.createObjectURL(blob);
  const now    = new Date();
  const pad    = n => String(n).padStart(2,'0');
  const fname  = `bookmarks_${now.getFullYear()}${pad(now.getMonth()+1)}${pad(now.getDate())}_${pad(now.getHours())}${pad(now.getMinutes())}${pad(now.getSeconds())}.json`;
  const a      = document.createElement('a');
  a.href       = url;
  a.download   = fname;
  a.click();
  URL.revokeObjectURL(url);
  showToast(`💾 ${fname} 저장 완료 (${items.length}개 북마크)`);
}

// 불러오기: 파일 선택 → 병합 or 덮어쓰기 선택
function importBookmarks() {
  const input = document.createElement('input');
  input.type  = 'file';
  input.accept = '.json';
  input.onchange = e => {
    const file = e.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = ev => {
      try {
        const payload = JSON.parse(ev.target.result);
        if (!payload.bookmarks || !payload.folders) {
          alert('올바른 북마크 파일이 아닙니다.'); return;
        }

        const mode = confirm(
          `북마크 ${Object.keys(payload.bookmarks).length}개, 폴더 ${payload.folders.length}개를 불러옵니다.\n\n` +
          `[확인] 기존 북마크와 병합\n[취소] 기존 북마크를 모두 지우고 교체`
        ) ? 'merge' : 'replace';

        if (mode === 'replace') {
          saveBM(payload.bookmarks);
          saveFL(payload.folders);
        } else {
          // 병합: 폴더 id 충돌 시 새 id 발급
          const existFL = loadFL();
          const existBM = loadBM();
          const idMap   = {}; // 파일의 old id → 병합 후 id

          payload.folders.forEach(f => {
            const dup = existFL.find(e => e.id === f.id);
            if (!dup) {
              existFL.push(f);
              idMap[f.id] = f.id;
            } else if (dup.name === f.name) {
              idMap[f.id] = dup.id; // 같은 이름 폴더면 그냥 매핑
            } else {
              // id 충돌 + 이름 다름 → 새 id 발급
              const newId = 'f_' + Date.now() + '_' + Math.random().toString(36).slice(2,6);
              existFL.push({ ...f, id: newId });
              idMap[f.id] = newId;
            }
          });

          Object.entries(payload.bookmarks).forEach(([key, fid]) => {
            existBM[key] = idMap[fid] || fid;
          });

          saveFL(existFL);
          saveBM(existBM);
        }

        ensureDefaultFolder();
        renderCurrentTab();
        renderBmFolderBar();
        updateBmBadge();
        const total = Object.keys(loadBM()).length;
        showToast(`📂 불러오기 완료 — 현재 북마크 ${total}개`);
      } catch(err) {
        alert('파일을 읽는 중 오류가 발생했습니다: ' + err.message);
      }
    };
    reader.readAsText(file, 'utf-8');
  };
  input.click();
}

// 토스트 메시지
function showToast(msg) {
  let toast = document.getElementById('bmToast');
  if (!toast) {
    toast = document.createElement('div');
    toast.id = 'bmToast';
    toast.style.cssText = `
      position:fixed; bottom:28px; left:50%; transform:translateX(-50%);
      background:#1e1e2e; color:#fff; padding:10px 20px; border-radius:8px;
      font-size:13px; z-index:9999; box-shadow:0 4px 14px rgba(0,0,0,.25);
      pointer-events:none; opacity:0; transition:opacity .25s;
    `;
    document.body.appendChild(toast);
  }
  toast.textContent = msg;
  toast.style.opacity = '1';
  clearTimeout(toast._timer);
  toast._timer = setTimeout(() => { toast.style.opacity = '0'; }, 2800);
}

// ══════════════════════════════════════════
//  팝업
// ══════════════════════════════════════════
let popKey=null, popFid=null;

function openPopup(e, catKey, idx) {
  e.stopPropagation();
  ensureDefaultFolder();
  const d = DATA[catKey][idx];
  const key = itemKey(d);
  const bm = loadBM();

  if (bm[key]) {
    if (confirm('북마크를 삭제하시겠습니까?')) {
      delete bm[key];
      saveBM(bm);
      renderCurrentTab();
      updateBmBadge();
      showToast('북마크가 삭제되었습니다.');
    }
    return;
  }

  popKey = key;
  popFid = latestFid();
  renderPopupFolders();
  document.getElementById('popNewInput').value = '';
  const popup = document.getElementById('popup');
  const ov    = document.getElementById('popOverlay');
  const rect  = e.currentTarget.getBoundingClientRect();
  let left = rect.right + 8, top = rect.top;
  if (left + 260 > window.innerWidth)  left = rect.left - 260;
  if (top  + 320 > window.innerHeight) top  = window.innerHeight - 320;
  popup.style.left = left + 'px';
  popup.style.top  = Math.max(10, top) + 'px';
  popup.classList.add('open');
  ov.style.display = 'block';
}

function closePopup() {
  document.getElementById('popup').classList.remove('open');
  document.getElementById('popOverlay').style.display = 'none';
  popKey = null;
}

function renderPopupFolders() {
  const fs = loadFL();
  const bm = loadBM();
  const lid = latestFid();
  const sorted = [...fs].sort((a,b) => b.t - a.t);
  document.getElementById('popFolderList').innerHTML = sorted.map(f => {
    const cnt = Object.values(bm).filter(id => id === f.id).length;
    const isSel = f.id === popFid;
    const isLatest = f.id === lid;
    return `<div class="pf-row ${isSel?'sel':''} ${isLatest?'latest':''}" onclick="selPopFolder('${f.id}')">
      <span class="pf-name">📁 ${f.name}</span>
      <span class="pf-cnt">${cnt}</span>
    </div>`;
  }).join('');
}

function selPopFolder(fid) { popFid = fid; renderPopupFolders(); }

function popCreateFolder() {
  const inp = document.getElementById('popNewInput');
  const name = inp.value.trim();
  if (!name) return;
  const fs = loadFL();
  if (fs.find(f => f.name === name)) { alert('같은 이름의 폴더가 있습니다.'); return; }
  const newId = 'f_' + Date.now();
  fs.push({id: newId, name, t: Date.now()});
  saveFL(fs);
  popFid = newId;
  inp.value = '';
  renderPopupFolders();
}

function confirmBM() {
  if (!popKey || !popFid) return;
  const bm = loadBM();
  if (bm[popKey] === popFid) { delete bm[popKey]; }
  else { bm[popKey] = popFid; }
  saveBM(bm);
  closePopup();
  renderCurrentTab();
  updateBmBadge();
}

// ══════════════════════════════════════════
//  북마크 탭
// ══════════════════════════════════════════
let activeFid = '__all__';

function promptNewFolder() {
  const name = prompt('새 폴더 이름 (최대 20자):', '');
  if (!name) return;
  const t = name.trim().slice(0,20);
  if (!t) return;
  const fs = loadFL();
  if (fs.find(f => f.name === t)) { alert('같은 이름의 폴더가 있습니다.'); return; }
  const newId = 'f_' + Date.now();
  fs.push({id: newId, name: t, t: Date.now()});
  saveFL(fs);
  activeFid = newId;
  renderBmFolderBar();
  renderBmView();
}

function deleteFolder(fid) {
  if (!confirm('폴더를 삭제하면 해당 폴더 북마크도 모두 해제됩니다. 계속할까요?')) return;
  saveFL(loadFL().filter(f => f.id !== fid));
  const bm = loadBM();
  Object.keys(bm).forEach(k => { if (bm[k] === fid) delete bm[k]; });
  saveBM(bm);
  if (activeFid === fid) activeFid = '__all__';
  renderBmFolderBar(); renderBmView(); renderCurrentTab(); updateBmBadge();
}

function setActiveFid(fid) { activeFid = fid; renderBmFolderBar(); renderBmView(); }

function renderBmFolderBar() {
  const fs  = loadFL();
  const bm  = loadBM();
  const lid = latestFid();
  const sorted = [...fs].sort((a,b) => b.t - a.t);
  const total  = Object.keys(bm).length;
  document.getElementById('folderChips').innerHTML =
    `<div class="chip ${activeFid==='__all__'?'active':''}" onclick="setActiveFid('__all__')">
       전체 <span class="chip-cnt">${total}</span>
     </div>` +
    sorted.map(f => {
      const cnt = Object.values(bm).filter(id => id === f.id).length;
      return `<div class="chip ${activeFid===f.id?'active':''} ${f.id===lid?'chip-latest':''}" onclick="setActiveFid('${f.id}')">
        📁 ${f.name} <span class="chip-cnt">${cnt}</span>
        <span class="chip-del" onclick="event.stopPropagation();deleteFolder('${f.id}')">&times;</span>
      </div>`;
    }).join('');
}

function renderBmView() {
  renderBmFolderBar();
  const bm   = loadBM();
  const fs   = loadFL();
  const fmap = Object.fromEntries(fs.map(f=>[f.id, f.name]));

  const seen = new Set();
  const list = [];
  Object.keys(DATA).forEach(catKey => {
    DATA[catKey].forEach(d => {
      const key = itemKey(d);
      const fid = bm[key];
      if (!fid) return;
      if (activeFid !== '__all__' && fid !== activeFid) return;
      if (seen.has(key)) return;
      seen.add(key);
      list.push({ d, catKey, fid });
    });
  });

  const s = sortState['bm'];
  list.sort((a, b) => {
    let va = a.d[s.col], vb = b.d[s.col];
    if (typeof va === 'string') { va = va.toLowerCase(); vb = vb.toLowerCase(); }
    return va < vb ? -s.dir : va > vb ? s.dir : 0;
  });

  document.getElementById('bmCountLabel').textContent =
    (activeFid === '__all__' ? '전체' : '이 폴더') + ' 북마크 ' + list.length + '개';

  const tbody = document.getElementById('bmBody');
  if (!list.length) {
    tbody.innerHTML = '<tr><td colspan="7" class="no-result">북마크된 상품이 없습니다.</td></tr>';
    return;
  }
  tbody.innerHTML = list.map(({d, catKey, fid}) => {
    const key      = itemKey(d);
    const fname    = fmap[fid] || '';
    const hl       = d.isNew ? 'hl-new' : d.isHotUp ? 'hl-up' : '';
    const biz      = d.biz === '사업자 전용' ? '<span class="badge-biz">사업자</span>' : '';
    const img      = d.img ? `<img src="${d.img}" class="thumb" loading="lazy" onerror="this.style.display='none'">` : '';
    const price    = d.priceNum > 0 ? d.priceNum.toLocaleString() + '원' : '-';
    const idx      = DATA[catKey].indexOf(d);
    const catLabel = CATEGORIES.find(c=>c.key===catKey)?.label || '';
    return `<tr class="${hl}">
      <td class="col-bm">
        <button class="bm-btn on" onclick="openPopup(event,'${catKey}',${idx})">★</button>
        ${fname ? `<div class="bm-fname">${fname}</div>` : ''}
      </td>
      <td class="col-rank"><span class="rank-num">${d.rank}</span></td>
      <td class="col-img">${img}</td>
      <td class="col-change">${chgHtml(d)}</td>
      <td class="col-title">
        <a href="${d.url}" target="_blank" class="title-link">${d.title}</a>${biz}
        <div class="cat-tag">${catLabel}</div>
      </td>
      <td class="col-price"><span class="price-val">${price}</span></td>
      <td class="col-qty"><span class="qty-val">최소 ${d.qty}개</span></td>
    </tr>`;
  }).join('');

  // 카드 레이아웃 (모바일)
  const cardList = document.getElementById('cards-bm');
  if (cardList) {
    cardList.innerHTML = list.map(({d, catKey, fid}) => {
      const fname    = fmap[fid] || '';
      const hl       = d.isNew ? 'hl-new' : d.isHotUp ? 'hl-up' : '';
      const price    = d.priceNum > 0 ? d.priceNum.toLocaleString() + '원' : '-';
      const chg      = chgHtml(d);
      const biz      = d.biz === '사업자 전용' ? '<span class="badge-biz">사업자</span>' : '';
      const newBadge = d.isNew ? '<span class="badge-new">NEW</span>' : '';
      const catLabel = CATEGORIES.find(c=>c.key===catKey)?.label || '';
      const idx      = DATA[catKey].indexOf(d);
      const imgUrl   = d.img || '';
      return `<div class="card ${hl}">
        <div class="card-img-wrap">
          ${imgUrl ? `<img src="${imgUrl}" loading="lazy" onerror="this.style.display='none'">` : ''}
          <span class="card-rank">${d.rank}위</span>
          <button class="card-bm on" onclick="openPopup(event,'${catKey}',${idx})">★</button>
        </div>
        <div class="card-body">
          <a href="${d.url}" target="_blank" class="card-title">${d.title}</a>
          <div>
            <div class="card-meta">
              <span class="card-price">${price}</span>
              <span class="card-change">${chg}</span>
              <span class="card-qty">최소 ${d.qty}개</span>
            </div>
            <div class="card-tags">${newBadge}${biz}<span class="cat-tag">${catLabel}</span>${fname ? `<span class="bm-fname">${fname}</span>` : ''}</div>
          </div>
        </div>
      </div>`;
    }).join('');
  }
}

function updateBmBadge() {
  const cnt = Object.keys(loadBM()).length;
  document.getElementById('bmBadge').textContent = cnt ? '(' + cnt + ')' : '';
}

// ══════════════════════════════════════════
//  탭 전환
// ══════════════════════════════════════════
let currentTab = 'all';

function switchTab(key) {
  currentTab = key;
  CATEGORIES.forEach(c => {
    const btn = document.getElementById('tab-' + c.key);
    if (btn) btn.classList.toggle('active', c.key === key);
  });
  CATEGORIES.forEach(c => {
    const view = document.getElementById('view-' + c.key);
    if (view) view.style.display = c.key === key ? '' : 'none';
  });
  if (key === 'bm') renderBmView();
  else render(key);
}

// ══════════════════════════════════════════
//  정렬
// ══════════════════════════════════════════
const sortState = {};
CATEGORIES.filter(c => c.key !== 'bm').forEach(c => {
  sortState[c.key] = { col: 'rankNum', dir: 1 };
});
sortState['bm'] = { col: 'rankNum', dir: 1 };
const TH_KEYS = ['rankNum','changeNum','title','priceNum'];

function sortByBm(col) {
  const s = sortState['bm'];
  s.dir = s.col === col ? s.dir * -1 : 1;
  s.col = col;
  TH_KEYS.forEach(k => {
    const el = document.getElementById(`th-bm-${k}`);
    if (!el) return;
    el.classList.remove('asc','desc');
    if (k === col) el.classList.add(s.dir===1?'asc':'desc');
  });
  renderBmView();
}

function sortBy(catKey, col) {
  const s = sortState[catKey];
  s.dir = s.col === col ? s.dir * -1 : 1;
  s.col = col;
  TH_KEYS.forEach(k => {
    const el = document.getElementById(`th-${catKey}-${k}`);
    if (!el) return;
    el.classList.remove('asc','desc');
    if (k === col) el.classList.add(s.dir===1?'asc':'desc');
  });
  render(catKey);
}


function sortBySelect(catKey, val) {
  const [col, dirStr] = val.split('_');
  const dir = parseInt(dirStr);
  const s = sortState[catKey];
  s.col = col;
  s.dir = dir;
  // 테이블 헤더 클래스도 동기화
  TH_KEYS.forEach(k => {
    const el = document.getElementById(`th-${catKey}-${k}`);
    if (!el) return;
    el.classList.remove('asc','desc');
    if (k === col) el.classList.add(dir===1?'asc':'desc');
  });
  render(catKey);
}

function resetAll(catKey) {
  ['search','priceMin','priceMax'].forEach(id => {
    const el = document.getElementById(`${id}-${catKey}`);
    if (el) el.value = '';
  });
  const biz = document.getElementById(`biz-${catKey}`);
  const hl  = document.getElementById(`hl-${catKey}`);
  if (biz) biz.value = '';
  if (hl)  hl.value  = '';
  sortState[catKey] = { col:'rankNum', dir:1 };
  TH_KEYS.forEach(k => {
    const el = document.getElementById(`th-${catKey}-${k}`);
    if (!el) return;
    el.classList.remove('asc','desc');
    if (k === 'rankNum') el.classList.add('asc');
  });
  render(catKey);
  const sortSel = document.getElementById(`sort-${catKey}`);
  if (sortSel) sortSel.value = 'rankNum_1';
}

function chgHtml(d) {
  if (d.isNew)          return '<span class="badge-new">NEW</span>';
  if (d.changeNum > 0)  return `<span class="chg-up">▲ ${d.changeNum}</span>`;
  if (d.changeNum < 0)  return `<span class="chg-down">▼ ${Math.abs(d.changeNum)}</span>`;
  return '<span class="chg-flat">-</span>';
}

// ══════════════════════════════════════════
//  렌더
// ══════════════════════════════════════════
function render(catKey) {
  const keyword  = (document.getElementById(`search-${catKey}`)?.value || '').trim().toLowerCase();
  const priceMin = parseInt(document.getElementById(`priceMin-${catKey}`)?.value) || 0;
  const priceMax = parseInt(document.getElementById(`priceMax-${catKey}`)?.value) || Infinity;
  const bizVal   = document.getElementById(`biz-${catKey}`)?.value || '';
  const hlVal    = document.getElementById(`hl-${catKey}`)?.value  || '';

  let list = (DATA[catKey] || []).filter(d => {
    if (keyword && !d.title.toLowerCase().includes(keyword)) return false;
    if (d.priceNum < priceMin || d.priceNum > priceMax)     return false;
    if (bizVal && d.biz !== bizVal)                          return false;
    if (hlVal === 'new'  && !d.isNew)                        return false;
    if (hlVal === 'up'   && !d.isHotUp)                      return false;
    if (hlVal === 'both' && !d.isNew && !d.isHotUp)          return false;
    return true;
  });

  const s = sortState[catKey];
  list.sort((a, b) => {
    let va = a[s.col], vb = b[s.col];
    if (typeof va === 'string') { va = va.toLowerCase(); vb = vb.toLowerCase(); }
    return va < vb ? -s.dir : va > vb ? s.dir : 0;
  });

  const countEl = document.getElementById(`count-${catKey}`);
  if (countEl) countEl.textContent = `총 ${list.length}개 표시 중 (전체 ${(DATA[catKey]||[]).length}개)`;

  const tbody = document.getElementById(`body-${catKey}`);
  if (!tbody) return;
  const bm = loadBM();

  if (!list.length) {
    tbody.innerHTML = `<tr><td colspan="7" class="no-result">검색 결과가 없습니다.</td></tr>`;
    return;
  }

  tbody.innerHTML = list.map(d => {
    const idx      = DATA[catKey].indexOf(d);
    const key      = itemKey(d);
    const isMarked = !!bm[key];
    const hl       = d.isNew ? 'hl-new' : d.isHotUp ? 'hl-up' : '';
    const biz      = d.biz === '사업자 전용' ? '<span class="badge-biz">사업자</span>' : '';
    const img      = d.img ? `<img src="${d.img}" class="thumb" loading="lazy" onerror="this.style.display='none'">` : '';
    const price    = d.priceNum > 0 ? d.priceNum.toLocaleString() + '원' : '-';
    const catTag = d.cat_label ? `<div class="cat-tag">${d.cat_label}</div>` : '';
    const allRankTag = (catKey === 'merged' && d.all_rank)
      ? `<div class="all-rank-sub">전체 ${d.all_rank}위</div>` : '';
    return `<tr class="${hl}">
      <td class="col-bm">
        <button class="bm-btn ${isMarked?'on':'off'}"
          title="${isMarked?'북마크 수정':'북마크 추가'}"
          onclick="openPopup(event,'${catKey}',${idx})">
          ${isMarked ? '★' : '☆'}
        </button>
      </td>
      <td class="col-rank"><span class="rank-num">${d.rank}</span>${allRankTag}</td>
      <td class="col-img">${img}</td>
      <td class="col-change">${chgHtml(d)}</td>
      <td class="col-title"><a href="${d.url}" target="_blank" class="title-link">${d.title}</a>${biz}${catTag}</td>
      <td class="col-price"><span class="price-val">${price}</span></td>
      <td class="col-qty"><span class="qty-val">최소 ${d.qty}개</span></td>
    </tr>`;
  }).join('');

  // 카드 레이아웃 (모바일)
  const cardList = document.getElementById(`cards-${catKey}`);
  if (cardList) {
    cardList.innerHTML = list.map(d => {
      const idx      = DATA[catKey].indexOf(d);
      const key      = itemKey(d);
      const isMarked = !!bm[key];
      const hl       = d.isNew ? 'hl-new' : d.isHotUp ? 'hl-up' : '';
      const price    = d.priceNum > 0 ? d.priceNum.toLocaleString() + '원' : '-';
      const chg      = chgHtml(d);
      const biz      = d.biz === '사업자 전용' ? '<span class="badge-biz">사업자</span>' : '';
      const catTag   = d.cat_label ? `<span class="cat-tag">${d.cat_label}</span>` : '';
      const newBadge = d.isNew ? '<span class="badge-new">NEW</span>' : '';
      const imgUrl   = d.img || '';
      return `<div class="card ${hl}">
        <div class="card-img-wrap">
          ${imgUrl ? `<img src="${imgUrl}" loading="lazy" onerror="this.style.display='none'">` : ''}
          <span class="card-rank">${d.rank}위</span>
          <button class="card-bm ${isMarked?'on':'off'}"
            onclick="openPopup(event,'${catKey}',${idx})">
            ${isMarked ? '★' : '☆'}
          </button>
        </div>
        <div class="card-body">
          <a href="${d.url}" target="_blank" class="card-title">${d.title}</a>
          <div>
            <div class="card-meta">
              <span class="card-price">${price}</span>
              <span class="card-change">${chg}</span>
              <span class="card-qty">최소 ${d.qty}개</span>
            </div>
            <div class="card-tags">${newBadge}${biz}${catTag}</div>
          </div>
        </div>
      </div>`;
    }).join('');
  }
}

function renderCurrentTab() {
  if (currentTab === 'bm') renderBmView();
  else render(currentTab);
}

// ── 초기화 ──
ensureDefaultFolder();
switchTab('all');
updateBmBadge();