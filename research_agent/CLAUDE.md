# CLAUDE.md — Research Agent 개발 규칙

## .bat 파일 작성 규칙

Windows CMD 한글 인코딩 문제를 방지하기 위해 반드시 아래 규칙을 따른다.

### 인코딩
- **UTF-8 (BOM 없음)** 으로 저장
- 첫 두 줄은 반드시:
  ```bat
  @echo off
  chcp 65001 >nul
  ```
- Write 툴 기본값(UTF-8)으로 저장 → 그대로 사용
- PowerShell `WriteAllText(..., GetEncoding(949))` 사용 금지 (CP949 저장은 오히려 UTF-8 환경에서 깨짐)

### 라인 엔딩
- **CRLF** 강제 적용 (CMD 안전성)
- 저장 후 PowerShell로 LF→CRLF 변환:
  ```powershell
  $c=[IO.File]::ReadAllText($p,[Text.Encoding]::UTF8)
  $c=$c -replace "`r`n","`n" -replace "`n","`r`n"
  [IO.File]::WriteAllText($p,$c,[Text.Encoding]::UTF8)
  ```

### PowerShell 인라인 명령
- `^` 멀티라인 연속 구문 사용 금지 (CMD 파싱 오류 발생)
- 반드시 **한 줄**로 작성:
  ```bat
  powershell -NoProfile -Command "$s=...; $s.Save()"
  ```

### Python 명령
- `py -3.12` 먼저 시도 → 없으면 `python` 폴백
- `set PYTHON_CMD=py -3.12` 또는 `set PYTHON_CMD=python` 방식으로 변수화

### 크로스머신 호환
- 이 PC: `py -3.12` 또는 `python` 모두 지원
- 노트북: 위 Python 폴백 로직으로 자동 처리
- 두 머신 모두 `chcp 65001 + UTF-8` 방식으로 통일
