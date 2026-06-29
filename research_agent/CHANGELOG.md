# CHANGELOG

## v2.0.0 (2026-06-29)

### New Features

#### 출력 품질 향상 (utils/export.py — 신규)
- **Word (.docx) 템플릿 개선**
  - Academic 모드: IEEE 논문 양식 (A4, 2.5cm 여백, 딥블루 제목·헤딩, Abstract 배경 강조)
  - Strategy 모드: 컨설팅 리포트 양식 (A4, 3cm 좌측 여백, 포레스트그린 테마)
  - Abstract 섹션 자동 감지 → 음영 배경 + 좌측 강조 테두리 적용
  - 본문 `**bold**` / `*italic*` / `` `code` `` 인라인 마크다운 → 실제 Run 스타일 변환
  - 코드 블록 회색 배경 + Courier New 폰트
  - 참고문헌 항목 행잉 인덴트 자동 적용
  - 제목·생성일·템플릿 라벨 표제 블록 추가
- **PDF 템플릿 개선**
  - 모드별 표지 페이지: 다크 배경, 상단/하단 악센트 바, 모드 라벨, 제목, 생성일
  - 본문 페이지 헤더: 문서 제목(단축) + 구분선 (표지 제외)
  - 본문 페이지 푸터: "Multi-Agent Research System | 날짜 | Page X / 전체" (표지 제외)
  - H1에 하단 구분선, H2에 연한 구분선 추가
  - 코드 블록 회색 배경, 한국어 폰트(맑은 고딕) 우선 적용

#### 연구 이력 DB (core/history_db.py — 신규)
- SQLite 기반 연구 이력 저장 (`research_history.db`)
- 주제·모드·날짜·점수·파일경로·소요시간 자동 저장
- Jaccard 유사도 기반 유사 연구 중복 체크 (threshold 0.35)
- 사이드바 `📊 연구 이력 보기` 버튼 → 이력 대시보드 (필터·검색·다운로드)
- 유사 연구 발견 시 사이드바 경고 표시

#### 참고문헌 자동 생성 (agents/reference_builder.py — 신규)
- Academic 모드: IEEE 형식, Strategy 모드: APA 형식
- Stage 6에서 수집 자료 기반으로 LLM이 참고문헌 자동 생성
- 결과 문서 말미에 `## References (IEEE/APA)` 섹션 자동 추가

### Improvements

#### 검색 품질 향상 (agents/manager.py)
- 모드별 분리 프롬프트: `PLAN_PROMPT_ACADEMIC` / `PLAN_PROMPT_STRATEGY`
- 검색어 5개 → 10개 (arxiv/survey/SOTA/알고리즘/오픈소스/한계점 유형 강제)
- 시스템 프롬프트 강화 (NeurIPS·ICML / McKinsey·Gartner 기준 명시)

#### 리뷰 점수 개선 (agents/reviewer.py)
- 페르소나별 5단계 점수 루브릭 명시 (0.55 / 0.65 / 0.75 / 0.85 / 1.0)
- 아이디어 단계 기본 점수 0.65 이상 가이드 추가
- REVIEW_PROMPT: 강점 3개 의무화, 약점은 개선 방향 포함 형식

#### Lit Agent 병렬 수 (config/settings.py)
- `max_parallel_queries`: 5 → 10 (검색 처리량 2배)

#### 파이프라인 (core/pipeline.py)
- Stage 6: 참고문헌 빌더 통합 (`ReferenceBuilder`)
- `state.references` 필드 추가 (core/state.py)

---

## v1.0.0 (2026-06-28)

### 최초 릴리즈

- 6단계 Multi-Agent 파이프라인 (Manager → Searcher → Summarizer → Ideation → Executor → Reviewer → Writer)
- Streamlit 대시보드 (실시간 Stage 카드, 리뷰 점수 게이지, 로그 패널)
- Academic / Strategy 듀얼 모드
- Markdown / Word / PDF 다운로드
- 이전 결과 보기 (사이드바 파일 선택)
- Multi-persona 리뷰 (Methodology Hawk · Novelty Skeptic · Impact Evaluator)
- Anthropic `web_search_20250305` 도구 기반 병렬 웹 검색
