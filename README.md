# 도매꾹 인기 랭킹 자동 크롤러

매일 자정 12시 15분마다 도매꾹 인기 랭킹을 자동으로 크롤링하여 날짜별로 저장합니다.

## 파일 구조

```
├── domeggook_crawler.py       # 크롤러 메인 스크립트
├── js_template.js             # HTML에 삽입되는 JS 템플릿
├── domeggook_ranking.html     # 최신 랭킹 뷰어 (자동 생성)
├── data/
│   ├── ranking_20250419.json  # 날짜별 크롤링 데이터
│   ├── ranking_20250420.json
│   └── ...
├── synology/
│   ├── api.php                # 시놀로지 북마크 API
│   └── bookmarks.json         # 북마크 데이터 (api.php와 같은 폴더에 위치)
└── .github/
    └── workflows/
        └── crawl.yml          # GitHub Actions 자동화 워크플로우
```

---

## 초기 설정

### 1. GitHub Actions 권한
- Repository → Settings → Actions → General
- **Workflow permissions: Read and write** 로 변경

### 2. GitHub Pages 설정
1. Repository → Settings → Pages
2. Source: `Deploy from a branch` → `main` / `/ (root)`
3. 접속 주소: `https://[username].github.io/[repo]/domeggook_ranking.html`

### 3. 첫 실행 (HTML 최초 생성)
- Actions 탭 → `Crawl Domeggook Rankings` → **Run workflow**

---

## 사용법

### 자동 크롤링
- 매일 **00:15 KST** (UTC 15:15) 자동 실행
- `data/ranking_YYYYMMDD.json` 저장
- `domeggook_ranking.html` 재생성 후 자동 커밋

### 수동 실행
```bash
pip install requests beautifulsoup4
python domeggook_crawler.py
```

---

## 뷰어 기능

### 날짜별 데이터 조회
- 상단 **날짜 선택 드롭다운**에서 원하는 날짜 선택
- 해당 날짜의 `data/ranking_YYYYMMDD.json` 을 fetch해서 테이블 갱신

### 카테고리 탭
- 전체 랭킹 / 카테고리별(패션잡화, 의류, 출산유아, 가구생활, 스포츠, 가전) / 카테고리 합산 / 북마크

### 필터 및 정렬
- 상품명 검색, 가격 범위, 구분(일반/사업자) 필터
- 정렬 기준 드롭다운: 순위 / 가격 낮은순·높은순 / 변동 상승순 / 가나다순
- PC에서는 테이블 헤더 클릭으로도 정렬 가능 (정렬 드롭다운과 동기화)

### 반응형 (모바일 지원)
- **640px 이하**: 테이블 대신 카드 레이아웃으로 전환
- 카드: 이미지 + 순위 뱃지 + 북마크 버튼 / 제목·가격·변동·수량
- 모바일에서도 필터·정렬 드롭다운 동일하게 사용 가능

### 다크모드
- 상단 제목 옆 **🌙 다크모드** 버튼으로 전환
- 설정은 브라우저 `localStorage`에 저장되어 새로고침 후에도 유지

### 북마크
- 상품마다 ☆ 버튼으로 폴더에 북마크 저장
- 폴더 생성·삭제 및 북마크 이동 가능
- JSON 파일로 내보내기 / 불러오기 지원
- **시놀로지 서버 연결 시 모든 브라우저에서 북마크 공유** (아래 참고)

---

## 시놀로지 북마크 서버 설정

북마크를 NAS에 저장해서 어느 브라우저에서 접속해도 동일한 북마크를 볼 수 있습니다.

### 사전 조건
- 시놀로지 DSM에 **Web Station** + **PHP** 패키지 설치
- 외부 접속 가능한 도메인 (예: `xxx.synology.me`)
- HTTPS 인증서 (Let's Encrypt 권장)

### 시놀로지 설정 순서

**1. 폴더 생성**
- File Station → `web/` 폴더 안에 `domeggook/` 폴더 생성

**2. 파일 업로드**
- `api.php`, `bookmarks.json` 을 `web/domeggook/` 에 업로드

**3. Secret Key 변경**
`api.php` 를 열어 아래 줄을 본인만 아는 문자열로 변경:
```php
define('SECRET_KEY', 'YOUR_SECRET_KEY_HERE');
```

**4. 쓰기 권한 설정**
- File Station → `domeggook/` 폴더 우클릭 → 속성 → 권한
- `http` 사용자에게 **읽기/쓰기** 허용

**5. 브라우저에서 연결**
- 뷰어 → 북마크 탭 → **🔗 서버 설정** 버튼 클릭
- API URL: `https://xxx.synology.me/domeggook/api.php`
- Secret Key: 위에서 설정한 값 입력 → **연결 저장**
- 버튼이 **"🔗 서버 연결됨"** (보라색)으로 바뀌면 성공

### 동작 방식
- 페이지 로드 시 서버에서 북마크 자동 불러오기
- 북마크 추가·삭제·폴더 변경 시 500ms 디바운스 후 자동 저장
- 서버 미설정 또는 연결 실패 시 기존처럼 메모리에서만 동작 (데이터 유실 없음)

### 기존 북마크 마이그레이션
기존에 내보낸 `bookmarks_YYYYMMDD_HHMMSS.json` 파일을
`bookmarks.json` 으로 이름 바꿔서 `web/domeggook/` 에 업로드하면
서버 연결 시 자동으로 불러옵니다.

---

## API 엔드포인트

| Method | URL | 설명 |
|--------|-----|------|
| GET | `/domeggook/api.php` | 북마크 불러오기 |
| POST | `/domeggook/api.php` | 북마크 저장 |

**인증**: 모든 요청에 `X-Secret-Key: [키값]` 헤더 필요

---

## 주의사항
- 크롤링 데이터는 `data/` 폴더에 누적 저장되므로 오래된 파일은 직접 삭제
- GitHub Actions는 공개 저장소에서 무료 사용 가능
- `api.php` 의 Secret Key는 절대 GitHub에 커밋하지 않도록 주의 (`.gitignore` 활용 권장)
