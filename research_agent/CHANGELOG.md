# CHANGELOG

## v3.1.8 (2026-07-06)

### 핵심 목표: 다중 URL 검색 결과에서 참고문헌 제목 반복 버그 수정

#### 참고문헌 제목-URL 매핑 수정 (agents/reference_builder.py)
- `_format_sources()`가 검색 쿼리 하나에 묶인 여러 URL(최대 3개)에 동일한 제목
  (요약 단계의 단일 문서 제목 또는 원본 쿼리 문자열)을 그대로 붙여 프롬프트에 전달하던
  문제 수정 — 서로 다른 실제 문서인데도 참고문헌에 같은 제목이 반복 노출됨
- 이제 소스(`sources`)마다 실제로 수집된 개별 `title`을 사용해 URL 1개당 줄 1개로 전달
  (최대 20개), 개별 제목이 없으면 요약/쿼리 제목으로 폴백
- `_dedupe_by_url()` 추가: 모델이 프롬프트의 중복 제거 지시를 놓쳐 같은 URL이 두 번
  나오는 경우를 대비한 안전장치 — 완전히 동일한 URL의 두 번째 이후 항목 제거
- 실제 LLM 호출로 검증: 쿼리 3개·소스 8개(QoS 논문형 다중 소스 검색 형태)로
  참고문헌을 재생성해 8건 전부 서로 다른 제목으로 반복 없이 생성됨을 확인

## v3.1.7 (2026-07-06)

### 핵심 목표: 논문 강화(섹션 보완) 결과를 대시보드에 노출

#### 기존 논문 강화 UI 개선 (app.py)
- academic 모드에서 버튼 라벨을 "🎨 그림·테이블 추가" → "🧠 논문 강화 (섹션 보완 +
  그림·표 추가)"로 변경해 실제 동작(섹션 보완 포함)을 정확히 반영, strategy 모드에는
  섹션 보완이 academic 전용임을 안내하는 캡션 추가
- 강화 완료 화면에 **섹션 완성도 검토 결과** 카드 추가 — 새로 생성/확장 재작성/그대로
  유지/실패 건수를 지표로 표시하고, `섹션별 상세 내역 보기` 펼치기에서 섹션별 처리
  결과(`section_report`)를 개별 확인 가능
- Streamlit 대시보드를 실제로 띄우고 Playwright로 조작해 버튼 라벨·결과 카드·다운로드
  버튼(Markdown/Word/PDF)이 모두 정상 렌더링됨을 확인

## v3.1.6 (2026-07-06)

### 핵심 목표: 논문 강화 시 섹션 보완 기능 추가 + PDF/Word 렌더링 데이터 유실 버그 수정

#### 논문 섹션 완성도 검토·보완 (tools/paper_enhancer.py)
- `SectionReviewer` 신규 추가: 기존 `.md` 논문에서 표준 섹션(Abstract~Conclusion)이
  빠져 있으면 새로 생성하고, 너무 짧은 섹션은 기존 내용을 유지하며 확장 재작성
  (`review_and_fill()`), canonical 순서를 유지하며 삽입 위치 자동 결정
- Writer/Executor와 동일한 잘림(`stop_reason=max_tokens`) 감지 후 재시도 로직 적용,
  빈 결과·실패 섹션은 경고 로그와 함께 건너뜀
- 그림·테이블 생성 단계를 각각 `try/except`로 감싸 한 단계 실패가 전체 강화를
  중단시키지 않도록 방어
- `PaperEnhancer.enhance()`가 `section_report`를 결과에 포함해 반환

#### PDF/Word 렌더링 치명적 데이터 유실 버그 수정 (utils/export.py)
- LLM이 생성한 ASCII 다이어그램 등에서 코드 펜스(```)가 닫히지 않은 채 다음
  섹션으로 넘어가면, `remove_ascii_art_blocks()`의 정규식이 그 사이에 있는 아무
  다음 펜스(예: 언어 태그가 붙은 Appendix 코드 펜스)까지를 통째로 하나의 코드
  블록으로 묶어 그 사이 실제 섹션 전체(Experiments/Discussion/Conclusion 등)를
  삭제해버리는 버그 확인 (실제 QoS 논문에서 문서의 절반 가까이 유실 재현)
- `_auto_close_unclosed_fences()` 추가: 펜스가 열린 채로 마크다운 헤딩을 만나면
  그 직전에 닫는 펜스를 강제 삽입, 문서 끝까지 열려 있으면 끝에서 닫음 —
  `to_pdf()`/`to_docx()` 맨 앞, 다른 전처리보다 먼저 적용
- 실제 QoS 논문으로 재현 후 수정 확인: PyMuPDF/python-docx로 텍스트 추출해
  Experiments/Discussion/Conclusion/References 전 섹션이 정상 렌더링됨을 검증

## v3.1.4 (2026-07-06)

### 핵심 목표: 응답 잘림(max_tokens) 감지·재시도, 기호/들여쓰기 렌더링 안전성 개선

#### 응답 잘림 감지 및 재시도 (core/base_agent.py, agents/writer.py, agents/executor.py)
- `call_llm()`에 `label`·`return_meta` 파라미터 추가 — `return_meta=True`면
  `(text, stop_reason)` 튜플 반환, `stop_reason == "max_tokens"`이면 verbose 여부와
  무관하게 항상 경고 로그 남김 (기본 동작은 기존과 동일해 기존 호출부는 영향 없음)
- Writer 섹션 생성·Executor 분석 코드 생성이 잘림을 감지하면 더 큰 토큰 상한
  (`MAX_TOKENS_SECTION_RETRY_CAP` 신규 설정값)으로 1회 재시도, 재시도에도 잘리면
  경고 로그와 함께 그대로 사용
- 참고문헌 생성 결과가 0건이면 경고 로그 추가 (agents/reference_builder.py)

#### 기호·들여쓰기 렌더링 안전성 (utils/export.py)
- `_normalize_symbols()` 추가: PDF 코어 폰트·임베딩 한글 폰트 모두 지원하지 않는
  체크마크류 기호(✓/✗ 등)를 ASCII 안전 표기(Yes/No)로 통일
- `_pdf_code()`가 `multi_cell` 기본 정렬(justify) 때문에 코드 블록 줄바꿈 시 들여쓰기가
  사라지던 문제 수정 — 선행 공백 보존 + `align="L"` 강제

## v3.1.3 (2026-07-04)

### 핵심 목표: Figure 1 라벨 잘림 수정, 인용/참고문헌 실제 근거 강제, ASCII 대체문 다국어 지원

#### Figure 1 아키텍처 다이어그램 라벨 잘림 수정 (agents/figure_builder.py)
- `steps = [s[:28] for s in steps]`로 라벨을 강제 절단하던 것을 제거
- `_fit_box_label()` 추가: matplotlib 렌더러로 실제 텍스트 폭을 측정해 박스 폭에 맞춰
  단어 단위 줄바꿈(최대 3줄)하고, 그래도 안 맞으면 폰트 크기를 단계적으로 축소 —
  텍스트를 자르지 않고 항상 전체 내용을 보존

#### 인용·참고문헌 근거 강제 (agents/searcher.py, reference_builder.py, writer.py)
- `searcher.py`: Anthropic 웹 검색 도구 응답에서 실제 검색 결과(URL/제목)를 `sources`로
  추출 — 속성(attribute) 스타일/dict 스타일 응답 구조 모두 방어적으로 처리
- `reference_builder.py`: 참고문헌 생성 프롬프트에 실제 title/url을 전달하고, 저자·연도·
  권호 등 근거 없는 정보를 지어내지 않도록 규칙 강화 ("Various Authors"·임의 연도 금지,
  근거 불명 시 "n.d." + 실제 title/URL 사용)
- `writer.py`: Introduction/Related Work 프롬프트에 번호가 매겨진 실제 참고문헌 목록을
  전달해 `[CITATION]` placeholder 대신 실제 `[n]` 번호로 인용하도록 지시. `_numbered_refs()`
  추가로 목록 순서를 References 섹션과 항상 일치시킴. 그래도 남은 `[CITATION]`은
  `[REF NEEDED]`로 명시 표시하고 경고 로그 남김 (실제 인용인 것처럼 보이는 것을 방지)

#### ASCII 아트 대체문 다국어 지원 (utils/export.py)
- `remove_ascii_art_blocks()`가 문서 언어(한글 비중 샘플링)에 따라 한국어 문서는
  "Figure N 참조", 영문 문서는 "See Figure N for the system architecture."로 대체하도록 개선

### 확인 필요 (다음 실제 파이프라인 실행 시)
- searcher/reference_builder/writer 변경은 실제 웹 검색을 포함한 파이프라인 실행에서만
  최종 검증 가능 — 본문 인용이 `[n]` 실제 번호로 나오는지, References에 실제 title/URL이
  나오는지 다음 실행 시 확인 필요

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
