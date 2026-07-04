# CHANGELOG

## v3.1.2 (2026-07-04)

### 핵심 목표: PDF 표 잘림 수정 + 위/아래첨자 렌더링 안전성 개선

#### PDF 표 자동 줄바꿈 (utils/export.py)
- `_pdf_table`이 셀 값을 `val[:22]`로 강제 절단하던 것을 제거 — `_pdf_wrap_text()` 추가로
  컬럼 폭에 맞춰 단어 단위 자동 줄바꿈, 필요한 만큼 행 높이가 늘어나며 페이지 하단을
  넘으면 자동으로 다음 페이지로 넘어감
- 셀을 사각형(rect)으로 직접 그려 여러 줄이어도 테두리·배경색이 깨지지 않도록 처리

#### 위/아래첨자 렌더링 안전성 (utils/export.py)
- `_apply_scripts()` 추가: `X^abc`, `X_abc` 형태를 `X^(abc)`, `X_(abc)` 괄호 표기로 통일
- 유니코드 위/아래첨자 글자(ₑ, ᵤ 등)로 변환하는 방식은 검토 후 배제 — 이 프로젝트가 쓰는
  한글 폰트(맑은 고딕)가 숫자 첨자 일부(0,5-9)와 문자 첨자 전부를 지원하지 않아, 변환 시
  예외 없이 글리프가 조용히 사라지는 문제(`C_e` → `C`)를 확인했기 때문. 폰트 지원 여부와
  무관하게 항상 안전한 ASCII 괄호 표기로 통일해 정보 손실을 방지

## v3.1.1 (2026-07-04)

### 핵심 목표: Word/PDF 출력 품질 개선 — 그림 삽입·수식·표 렌더링 버그 수정

#### 그림/표 렌더링 버그 수정 (utils/export.py, app.py)
- **저장된 문서 재열람 시 그림 미삽입 수정**: "이전 결과 보기"·"기존 논문 강화" 재열람 경로가 `figures` 파라미터 없이 `to_docx`/`to_pdf`를 호출해 `[Saved: path]` 텍스트만 남던 문제 — `_load_figures_from_md()` 추가로 문서의 Figures 섹션에서 실제 PNG를 디스크에서 복구해 항상 이미지가 삽입되도록 수정
- **표 셀 마크다운 잔재 제거**: `_parse_md_table`이 `**bold**` 등 인라인 마크다운을 제거하지 않아 표에 별표가 그대로 노출되던 문제 수정
- **PDF 표 색상 렌더링 견고화**: `_pdf_table` 셀에 `_pdf_safe`와 동일한 latin-1 폴백 추가 — 한글 폰트가 없는 환경에서도 배경색·테두리가 항상 유지되도록 개선

#### LaTeX 수식 → 평문 변환 (utils/export.py)
- `preprocess_math()` 추가: `$...$`, `$$...$$` 수식을 Word/PDF 변환 전에 읽을 수 있는 평문으로 치환
  - 인라인 수식은 괄호·기호를 풀어쓴 텍스트로 문장에 그대로 삽입 (예: `$G = (V, E)$` → `G = (V, E)`)
  - 블록 수식은 `*[수식] ...*` 형태의 독립된 줄로 변환
  - `\frac`, `\sqrt`, `\underbrace`, `\text`, `\mathbb`, 그리스 문자 등 처리, 코드 블록은 보존

#### ASCII 아트 박스 제거 (utils/export.py)
- `remove_ascii_art_blocks()` 추가: 박스 드로잉 문자(┌─┐ 등)로 그려진 텍스트 다이어그램을 "OO는 Figure N 참조" 텍스트로 대체 — 뒤에 삽입되는 실제 Figure PNG와의 중복 제거 (언어 태그가 있는 코드 펜스는 보존)

#### 표지/헤더 파일명 노출 수정 (app.py)
- `_doc_title()` 추가: 문서의 실제 제목(H1)을 추출해 표지·헤더에 표시 — 기존에는 파일명(타임스탬프 포함)이 그대로 노출되던 문제 수정

## v3.1.0 (2026-07-02)

### 핵심 목표: 논문 출력 품질 자동화 — 4종 그림·테마 테이블·인라인 삽입

#### 그림 4종 자동 생성 (agents/figure_builder.py 전면 개선)
- **Figure 1: 아키텍처 다이어그램** — 실험 steps 기반 박스+화살표 플로우 (matplotlib Fancy Patch)
  - 제안 모듈(중앙) 오렌지 강조, 지원 컴포넌트 블루 그라데이션
  - `★ Proposed` 레이블·범례 자동 표시
- **Figure 2: 성능 비교 바 차트** — model_comparison 테이블 파싱, 제안 방법 오렌지 강조
- **Figure 3: Ablation Study 수평 바 차트** — ablation 테이블 파싱
- **Figure 4: 리뷰 점수 레이더 차트** (신규) — 3개 페르소나 점수 + Overall·Feasibility·Clarity 6축 레이더
- 모든 그림 PNG → `outputs/figures/figure_N_*.png` 자동 저장
- **모든 모드** (academic·strategy) 에 적용 (`if self.mode == "academic"` 제거)

#### 파이프라인 개선 (core/pipeline.py)
- **그림 생성 시점 변경**: Stage 6-d(Writer 후) → **6-c(Writer 전)** — state.figures 경로를 Writer가 참조 가능
- `## Figures 섹션 자동 추가` (6-e): 최종 문서에 그림 제목·캡션·파일경로 마크다운으로 삽입
- 모든 모드에서 그림 생성 실행

#### Word/PDF 출력 품질 향상 (utils/export.py)
- **Word 테이블**: `_xml_cell_border()` 추가 — 헤더 흰색 테두리, 데이터 셀 명시적 `#CCCCCC` 테두리 XML (모든 Word 버전에서 일관 렌더링)
- **PDF 테이블**: 짝수 행 교차 음영을 하드코딩 파란색(`235,240,255`) → **테마 `light` 색상** 사용 (strategy 모드에서 연두색 적용)
- **인라인 그림 삽입**: `## Figures` 섹션이 마크다운에 존재하면 `### Figure N:` 헤딩 위치에 PNG 직접 삽입 (캡션·저장경로 줄 자동 스킵)
- 구버전 문서(Figures 섹션 없음) 호환: appendix 방식 폴백

---

## v3.0.0 (2026-06-30)

### 핵심 목표: 논문 완성도 향상

#### Writer Agent 섹션별 분할 생성 (agents/writer.py 전면 재작성)
- 기존 단일 호출 → **7개 섹션 독립 LLM 호출** (Abstract / Introduction / Related Work / Methodology / Experiments / Discussion / Conclusion)
- 각 섹션 전용 프롬프트로 품질 대폭 향상 (섹션당 최대 3,000 토큰)
- 섹션 생성 완료 시 대시보드 로그에 실시간 표시 (`✓ Section: ...`)
- Strategy 모드: 7개 섹션 (Executive Summary / Background / Landscape / Issues / Implications / Recommendations / Conclusion)

#### 실험 섹션 강화 (agents/executor.py)
- `generate_tables()` 메서드 추가 (Worker 모델 호출)
- **3종 비교 테이블 자동 생성**: 모델 성능 비교 / 실험 환경 / Ablation Study
- 테이블이 Writer의 Experiments 섹션 프롬프트에 직접 주입 → 결과 분석 자동화

#### 그림·차트 자동 생성 (agents/figure_builder.py 신규)
- Matplotlib 기반 **성능 비교 바 차트** 자동 생성 (제안 방법 오렌지색 강조)
- **Ablation Study 수평 바 차트** 자동 생성
- PNG bytes 형태로 `state.figures`에 저장

#### 결론 섹션 완성 강제
- `_enforce_conclusion()`: Conclusion < 200자이면 Future Work 자동 보완
- Conclusion 프롬프트에 `### 6.1 Summary` + `### 6.2 Future Work` 구조 강제
- Future Work 3개 방향 이상 의무화

#### Word/PDF 품질 향상 (utils/export.py)
- **마크다운 테이블 자동 파싱** → Word 표 변환 (헤더 색상·줄무늬·셀 정렬)
- **그림 자동 삽입**: Word `doc.add_picture()` + 이탤릭 캡션
- PDF 표 렌더링: 헤더 색상 배경 + 줄무늬 행
- PDF 그림 삽입: `pdf.image()` + 캡션
- 문서 말미에 "Figures" appendix 섹션 자동 추가
- `to_docx()` / `to_pdf()` 시그니처에 `figures: list` 파라미터 추가

#### 상태 관리 (core/state.py)
- `section_documents: dict` — 섹션별 생성 텍스트 저장
- `experiment_tables: dict` — 생성된 마크다운 테이블
- `figures: list` — `{title, caption, png_bytes}` 목록

#### 대시보드 (app.py)
- 버전 배지 v2.0.0 → **v3.0.0**
- 섹션 완료 실시간 감지 (`section_progress` session state)
- `figures` session state → 다운로드 시 Word/PDF에 자동 포함

---

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
