# 도매꾹 인기 랭킹 자동 크롤러

매일 자정 12시 15분마다 도매꾹 인기 랭킹을 자동으로 크롤링하여 날짜별로 저장합니다.

## 파일 구조

```
├── domeggook_crawler.py     # 크롤러 메인 스크립트
├── js_template.js           # HTML에 삽입되는 JS 템플릿
├── domeggook_ranking.html   # 최신 랭킹 뷰어 (자동 생성)
├── data/
│   ├── ranking_20250425.json   # 날짜별 크롤링 데이터
│   ├── ranking_20250426.json
│   └── ...
└── .github/
    └── workflows/
        └── crawl.yml        # GitHub Actions 자동화 워크플로우
```

## 사용법

### GitHub Actions 자동 실행
- 매일 **00:15 KST** (UTC 15:15) 자동 크롤링
- 결과는 `data/ranking_YYYYMMDD.json`에 저장
- `domeggook_ranking.html` 자동 갱신 후 커밋

### 수동 실행
```bash
pip install requests beautifulsoup4
python domeggook_crawler.py
```

### GitHub Pages 설정
1. Repository → Settings → Pages
2. Source: `Deploy from a branch` → `main` / `/ (root)`
3. `https://[username].github.io/[repo]/domeggook_ranking.html` 로 접근

## 날짜별 데이터 조회
- 뷰어 상단의 **날짜 선택 드롭다운**에서 원하는 날짜 선택
- 해당 날짜의 랭킹 데이터가 바로 로드됨
- 북마크는 브라우저 로컬스토리지에 저장 (날짜 무관)

## 주의사항
- 크롤링 데이터는 `data/` 폴더에 누적 저장됨
- 오래된 데이터 정리가 필요하면 `data/` 폴더에서 직접 삭제
- GitHub Actions는 공개 저장소에서 무료로 사용 가능
