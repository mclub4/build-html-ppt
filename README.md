<p align="center">
  <img src="assets/readme-hero.svg" alt="Build HTML Slides for Codex and Claude Code" width="100%" />
</p>

<p align="center">
  <a href="https://github.com/mclub4/build-html-ppt/releases"><img alt="Release" src="https://img.shields.io/github/v/release/mclub4/build-html-ppt?color=f06b52" /></a>
  <a href="LICENSE"><img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-57c7b6" /></a>
  <img alt="Codex and Claude Code" src="https://img.shields.io/badge/support-Codex%20%2B%20Claude%20Code-20252b" />
</p>

<h1 align="center">Build HTML Slides</h1>

<p align="center">
  Codex와 Claude Code가 발표의 대상과 목적을 먼저 읽고, 보기 좋은 HTML 슬라이드와 발표 노트까지 완성하도록 만든 프레젠테이션 스킬입니다.
</p>

> **OpenAI Codex CLI / Codex App과 Anthropic Claude Code를 지원**합니다. 이 저장소는 커뮤니티 프로젝트이며 OpenAI 또는 Anthropic의 공식 프로젝트가 아닙니다.

## 현재 상태

HTML 기반 PPT 제작 스킬을 시범적으로 개발했습니다. 발표 자료를 HTML로 구성하면 AI가 슬라이드 구조와 개별 요소에 직접 접근할 수 있어, 내용·배치·디자인을 세밀하게 수정하고 사용자의 요구사항을 구체적으로 반영하기 좋습니다.

현재는 테스트 단계이며 데스크톱 발표 환경을 우선합니다. 모바일 대응을 요청하고 별도로 검증한 덱이 아니라면 작은 화면에서 일부 요소가 정상적으로 표시되지 않을 수 있습니다.

제작 모드는 두 가지입니다.

- **초안 제작 모드(Quick Draft)**: 전체 이야기 구조와 디자인을 빠르게 만들고, 자동 검사를 중심으로 기본적인 잘림과 배치 문제를 확인합니다.
- **정밀 검증 모드(Full Validation)**: 모든 슬라이드를 렌더링해 구성·내용·배치·이미지를 세부적으로 검토하고 보완합니다.

약 15장 분량을 기준으로 초안 제작에는 약 10분, 정밀 검증에는 약 40~50분이 걸립니다. 이 수치는 **Codex GPT-5.6, 추론 강도 Medium**과 렌더링 도구가 이미 설치된 환경에서 측정한 대략적인 기준이며, Claude Code에서는 선택한 모델과 effort에 따라 달라질 수 있습니다. 20~25장 정밀 검증은 40~90분 완료를 목표로 하며, 팬아트·이미지 대량 탐색으로 90분을 넘길 전망이면 현재 후보를 확정할지 탐색을 계속할지 사용자에게 확인합니다.

## 실제 생성 예시

아래 이미지는 이 스킬로 만든 HTML 프레젠테이션을 Chromium에서 직접 렌더링한 결과입니다. 홍보용 키 비주얼부터 여행·음식 에디토리얼, 스포츠 데이터, 기술 시스템 흐름까지 발표 주제에 맞춰 서로 다른 구성을 사용합니다. 각 이미지는 전체 PPT 중 일부 슬라이드만 골라 소개한 것입니다.

<table>
  <tr>
    <td width="33.33%">
      <img src="assets/showcase/blue-archive-kivotos.webp" alt="블루 아카이브 팬 창작 생태계 소개 슬라이드" />
      <br /><strong>게임 문화 · 팬 생태계</strong>
    </td>
    <td width="33.33%">
      <img src="assets/showcase/f1-strategy.webp" alt="F1 입문 가이드 표지 슬라이드" />
      <br /><strong>스포츠 입문 · 레이스 가이드</strong>
    </td>
    <td width="33.33%">
      <img src="assets/showcase/hallyu-fandom-flow.webp" alt="K-POP 팬덤 확산 구조 슬라이드" />
      <br /><strong>문화 산업 · 팬덤 흐름</strong>
    </td>
  </tr>
  <tr>
    <td width="33.33%">
      <img src="assets/showcase/world-cuisine-plate.webp" alt="한 접시에서 세계 음식의 역할을 비교하는 슬라이드" />
      <br /><strong>음식 에디토리얼 · 역할 비교</strong>
    </td>
    <td width="33.33%">
      <img src="assets/showcase/rescene-character.webp" alt="리센느 멤버 캐릭터 소개 슬라이드" />
      <br /><strong>아이돌 홍보 · 캐릭터 스토리</strong>
    </td>
    <td width="33.33%">
      <img src="assets/showcase/manosaba-trial.webp" alt="마법소녀의 마녀재판 재판 구조 슬라이드" />
      <br /><strong>게임 홍보 · 키 비주얼</strong>
    </td>
  </tr>
  <tr>
    <td width="33.33%">
      <img src="assets/showcase/car-camping-destination.webp" alt="차박 여행지 시설 정보 슬라이드" />
      <br /><strong>여행 가이드 · 목적지 정보</strong>
    </td>
    <td width="33.33%">
      <img src="assets/showcase/mars-space-garden.webp" alt="우주 식물 재배 사진을 사용한 화성 기지 운영 슬라이드" />
      <br /><strong>기술 설계 · 우주 현장</strong>
    </td>
    <td width="33.33%">
      <img src="assets/showcase/manchester-united-legacy.webp" alt="올드 트래퍼드를 배경으로 한 맨체스터 유나이티드 표지 슬라이드" />
      <br /><strong>스포츠 홍보 · 클럽 서사</strong>
    </td>
  </tr>
  <tr>
    <td width="33.33%">
      <img src="assets/showcase/bluearchive-character-showcase.webp" alt="블루 아카이브 레이사 캐릭터와 팬아트 큐레이션 슬라이드" />
      <br /><strong>게임 캐릭터 · 팬아트 큐레이션</strong>
    </td>
    <td width="33.33%">
      <img src="assets/showcase/nintendo-switch2-promo.webp" alt="닌텐도 스위치 2와 마리오 카트 월드 홍보 슬라이드" />
      <br /><strong>제품 홍보 · 게임 경험</strong>
    </td>
    <td width="33.33%">
      <img src="assets/showcase/alien-invasion-scenario.webp" alt="외계 함대가 도시 상공에 나타난 침공 시나리오 슬라이드" />
      <br /><strong>SF 시나리오 · 침공 서사</strong>
    </td>
  </tr>
  <tr>
    <td width="33.33%">
      <img src="assets/showcase/showcase-placeholder.webp" alt="" />
      <br /><strong>추후 추가 예정</strong>
    </td>
    <td width="33.33%">
      <img src="assets/showcase/showcase-placeholder.webp" alt="" />
      <br /><strong>추후 추가 예정</strong>
    </td>
    <td width="33.33%">
      <img src="assets/showcase/showcase-placeholder.webp" alt="" />
      <br /><strong>추후 추가 예정</strong>
    </td>
  </tr>
</table>

게임명, 로고, 캐릭터 및 기타 제3자 자료의 권리는 각 권리자에게 있습니다. 예시 이미지는 스킬의 출력 형식과 디자인 범위를 설명하기 위해 사용합니다.

## 무엇을 만드나요?

한 번의 요청으로 다음 산출물을 함께 만듭니다.

- 오프라인에서도 열리는 단일 HTML 프레젠테이션
- 슬라이드별 발표 노트 Markdown
- 이미지 URL, 해시, 확인일을 보관하는 `sources.json`
- 키보드, 클릭, 페이지 번호 입력, 전체 화면을 지원하는 발표용 내비게이션
- 인쇄, 짧은 화면, 확대 환경을 고려한 반응형 무대

단순히 내용을 카드에 나누는 템플릿이 아닙니다. 발표 대상, 의사결정자, 배경지식, 반론 가능성을 바탕으로 이야기 순서를 정하고 주제에 맞는 테마와 시각 자료를 선택합니다.

## 발표자 노트 예시

HTML과 함께 생성되는 `OUTPUT-notes.md`에는 슬라이드별 목적, 실제로 읽을 수 있는 발표 멘트, 강조점, 다음 장으로 넘어가는 문장을 정리합니다. 근거가 필요한 내용에는 출처와 주의사항도 함께 남깁니다.

> **10. 자율 판단 루프**
>
> **목적:** AI를 통제되지 않은 대장으로 두지 않고 정책 가드레일 안의 판단 도구로 배치한다.
>
> **발표 멘트:** “관측, 예측, 결정, 실행, 학습이 반복되지만 전부 권한과 금지 규칙 안에서 움직입니다. 기계는 빠른 계산과 반복 복구를 맡고, 생명 위험과 비가역 조치는 사람이 결정합니다.”
>
> **전환:** “이제 실제로 펌프가 멈췄다고 가정해 보겠습니다.”

## 주요 기능

| 영역 | 지원 내용 |
| --- | --- |
| 스토리 | 임원, 사업, 개발, 고객, 투자자 등 청중에 맞춘 정보 순서와 깊이 |
| 디자인 | 주제별 테마, 공식 브랜드 자산, WebP 이미지, 열린 레이아웃, 다이어그램 |
| 이미지 안전성 | 키 비주얼 잘림 방지, 왜곡 탐지, 저해상도 경고, 출처·해시 캐시, 캐릭터/인물 기준 이미지 대조 |
| 발표 경험 | 애니메이션, 직접 페이지 이동, 전체 화면, 키보드와 클릭 내비게이션 |
| 검증 | 텍스트 이탈, 컨트롤, 이미지 geometry 자동 차단 후 내용 적합성과 캐릭터 동일성을 포함한 AI 시각 검토 |
| 수정 속도 | 바뀐 슬라이드와 앞뒤 슬라이드만 재렌더하고 변경 유형에 맞는 검사만 실행 |

## 이미지 생성 도구

이미지 생성은 선택 사항입니다. Codex에서 ImageGen이 제공되거나 Claude Code에 이미지 생성 플러그인·MCP가 연결된 경우에는 분위기 이미지, 에디토리얼 일러스트, 개념 장면, 배경 제작에 활용합니다.

Claude Code 기본 설치에는 이미지 생성기가 포함되지 않습니다. 생성 도구가 없어도 공식·사용자 제공·웹에서 조사한 이미지와 HTML/CSS 다이어그램으로 작업을 계속하며, 브라우저 사전 검사를 실패 처리하지 않습니다. 사용자가 생성 이미지를 명시적으로 요구했는데 도구가 없다면 임의로 설치하지 않고 대체 이미지로 진행할지 생성 도구를 구성할지 먼저 확인합니다.

## 설치 전 준비

필수 도구:

- [OpenAI Codex CLI](https://developers.openai.com/codex/cli/) 또는 [Anthropic Claude Code](https://code.claude.com/docs/en/overview) 최신 버전
- Python 3.10 이상
- Node.js 18 이상
- Playwright와 Chromium

Codex CLI가 없다면 macOS/Linux/WSL에서 다음 공식 설치 명령을 사용할 수 있습니다.

```bash
curl -fsSL https://chatgpt.com/codex/install.sh | sh
```

Claude Code 설치는 공식 문서를 따르세요. 설치 후 `claude --version`으로 확인할 수 있습니다.

이 저장소를 받은 뒤 렌더링 의존성을 설치합니다.

```bash
npm install
npx playwright install chromium
```

Linux/WSL에서 Chromium 시스템 라이브러리까지 필요하면 다음을 사용합니다.

```bash
npx playwright install --with-deps chromium
```

설치 확인:

```bash
npm run check:browser
```

`Pillow`, `cwebp`, ImageMagick은 선택 사항입니다. PNG 메타데이터 검사 속도를 높이거나 외부 이미지를 WebP로 일괄 변환할 때 유용하지만 스킬 실행의 필수 조건은 아닙니다.

릴리스 ZIP 생성은 Python 표준 라이브러리를 사용하므로 별도의 `zip` 패키지가 필요하지 않습니다.

## 설치

각 플랫폼에서 **플러그인과 단독 스킬 중 하나만** 선택하세요. 같은 플랫폼에 둘 다 설치하면 스킬이 중복 표시될 수 있습니다.

### 방법 A. Claude Code 플러그인

```bash
claude plugin marketplace add mclub4/build-html-ppt
claude plugin install build-html-slides@build-html-slides
```

설치 후 새 세션에서 자연어로 요청하거나 `/build-html-slides:build-html-slides`를 실행합니다. Claude 플러그인에는 독립 시각 검토자와 최종 품질 편집자 서브에이전트가 함께 포함됩니다.

### 방법 B. Codex 플러그인

```bash
codex plugin marketplace add mclub4/build-html-ppt
codex plugin add build-html-slides@build-html-slides
```

팀 배포, 버전 관리, Codex 플러그인 UI 사용에는 이 방법을 권장합니다.

### 방법 C. 단독 스킬

```bash
git clone https://github.com/mclub4/build-html-ppt.git
cd build-html-ppt
./install.sh
```

기본 설치는 감지된 Claude Code와 Codex에 각각 심링크를 연결합니다. 한 플랫폼에만 설치하려면 다음 옵션을 사용합니다.

```bash
./install.sh --claude-only
./install.sh --codex-only
```

Claude 스킬은 `~/.claude/skills/build-html-slides`, Codex 스킬은 `~/.codex/skills/build-html-slides`에 설치됩니다. 저장소 없이 복사본을 유지하려면 `./install.sh --copy`를 함께 사용하세요.

```bash
./update.sh       # 최신 버전으로 업데이트
./uninstall.sh    # 이 저장소가 설치한 단독 스킬 제거
```

설치 후에는 새 Claude Code 세션 또는 Codex 작업을 시작해야 변경된 스킬과 검토 에이전트를 안정적으로 불러옵니다.

## 사용법

자연어로 부탁하거나 플랫폼별 스킬 이름을 직접 지정할 수 있습니다.

Claude Code 플러그인:

```text
/build-html-slides:build-html-slides
사업팀, 개발팀, 대표님에게 신규 결제 인프라 전환안을 설명할 발표자료를 만들어줘.
```

Claude Code 단독 스킬은 `/build-html-slides`, Codex는 `$build-html-slides`를 사용합니다.

```text
$build-html-slides
사업팀, 개발팀, 대표님에게 신규 결제 인프라 전환안을 설명할 발표자료를 만들어줘.
의사결정이 필요한 내용은 앞에 두고, 구현 세부사항은 뒤에 배치해줘.
```

```text
이 HTML 발표자료에서 7번 슬라이드 이미지만 교체해줘.
수정된 슬라이드만 다시 렌더링해서 잘림과 비율을 꼼꼼히 검토해줘.
```

일반 수정은 새 검증 근거가 필요한 요청이 아니라면 빠른 **Edit Only**로 처리합니다. 새 덱은 사용자가 모드를 이미 지정하지 않은 이상 작업을 시작하기 전에 Quick Draft와 Full Validation의 차이를 제시하고 어떤 모드로 만들지 먼저 확인합니다.

모드가 정해지면 Quick Draft와 Full Validation 모두 공통 환경 검사를 실행합니다.

```bash
python3 codex/skills/build-html-slides/scripts/check_environment.py
# Claude 배포본에서는 .claude/skills/build-html-slides/scripts/check_environment.py
```

Python, Node.js, Playwright 또는 Chromium이 없거나 호환되지 않으면 누락 항목을 먼저 알리고 설치 여부를 묻습니다. 사용자가 동의하기 전에는 패키지 설치나 시스템 변경을 실행하지 않습니다.

실제 검증은 개별 스크립트를 기억해 조합하지 않고 단일 진입점으로 실행합니다. 20~25장 Full Validation은 일반적으로 40~90분을 목표로 하며, 이미지 대량 탐색 때문에 이를 넘길 전망이면 현재 후보를 확정할지 탐색을 이어갈지 먼저 확인합니다.

```bash
python3 codex/skills/build-html-slides/scripts/validate_all.py OUTPUT.html --mode quick --phase prepare
python3 codex/skills/build-html-slides/scripts/validate_all.py OUTPUT.html --mode full --review-risk standard --phase prepare
```

## 작업 파일 위치

최종 프레젠테이션 폴더에는 HTML, 발표자 노트, `sources.json`, 실제 사용 자산만 남깁니다. 렌더 캡처, 검토 매니페스트, 문구 초안, 접촉 시트 같은 작업 파일은 덱별로 다음 경로에 모입니다.

```text
~/.codex/build-html-slides/workspaces/<덱이름>-<경로해시>/   # Codex
~/.claude/build-html-slides/workspaces/<덱이름>-<경로해시>/  # Claude Code
├── review/   # Chromium 캡처와 검토 매니페스트
├── drafts/   # 문구·구성 초안
└── tmp/      # 접촉 시트와 임시 변환물
```

경로 확인과 정리:

```bash
node codex/skills/build-html-slides/scripts/render_slides.js --workspace-dir OUTPUT.html
node codex/skills/build-html-slides/scripts/render_slides.js --clean-workspace OUTPUT.html
```

같은 덱을 다시 수정할 때는 최신 검토 근거를 재사용하므로 불필요한 실행별 폴더가 쌓이지 않습니다. 작업공간 루트는 `BUILD_HTML_SLIDES_WORKSPACE_ROOT`로 변경할 수 있습니다.

## 함께 쓰면 좋은 스킬

한국어 슬라이드 문구와 발표 노트를 더 자연스럽게 다듬고 싶다면 [epoko77-ai/im-not-ai](https://github.com/epoko77-ai/im-not-ai)의 `humanize-korean` 스킬을 함께 쓰는 것을 권장합니다.

이 프로젝트의 필수 의존성은 아닙니다. 사실, 수치, 고유명사를 확정한 뒤 최종 문구 윤문 단계에 선택적으로 적용하세요.

## 검증과 개발

```bash
npm install
npx playwright install chromium
npm run check
npm run check:browser
npm run test:unit  # 빠른 결정적 검증
npm run test:e2e   # 실제 Chromium 렌더 파이프라인
npm test           # 전체 Python·Chromium 회귀 테스트
claude plugin validate .claude-plugin/plugin.json --strict
claude plugin validate .claude-plugin/marketplace.json --strict
```

공통 스킬을 수정한 뒤 Codex 플러그인과 Claude 배포본을 동기화합니다.

```bash
./scripts/sync-distributions.sh
```

플랫폼과 배포 방식을 구분한 릴리스 ZIP 네 개를 만들 수 있습니다.

```bash
./scripts/package-release.sh
```

생성 파일:

- `BUILD-HTML-SLIDES-CODEX-SKILL-vX.Y.Z.zip`
- `BUILD-HTML-SLIDES-CODEX-PLUGIN-vX.Y.Z.zip`
- `BUILD-HTML-SLIDES-CLAUDE-SKILL-vX.Y.Z.zip`
- `BUILD-HTML-SLIDES-CLAUDE-PLUGIN-vX.Y.Z.zip`

## 저장소 구조

```text
codex/skills/build-html-slides/             # 단독 Codex 스킬
plugins/build-html-slides/                  # Codex 플러그인
.agents/plugins/marketplace.json            # 공개 플러그인 마켓플레이스
.claude/skills/build-html-slides/            # Claude Code 스킬
.claude-plugin/                              # Claude Code 플러그인·마켓플레이스
agents/                                      # Claude 독립 시각 검토 에이전트
scripts/                                    # 동기화, 검증, 릴리스 패키징
```

## 로드맵

- [x] Codex CLI / Codex App 스킬
- [x] Codex Plugin 마켓플레이스 배포
- [x] Claude Code 스킬 및 Plugin 마켓플레이스 배포
- [ ] Gemini CLI 지원
- [ ] 더 많은 내보내기 및 협업 워크플로

지원 범위는 검증 가능한 형태로 하나씩 늘릴 예정입니다.

## 라이선스

[MIT License](LICENSE). 상업적/비상업적 목적을 가리지 않고 사용, 복사, 수정, 배포, 재라이선스, 판매할 수 있습니다. 재배포할 때는 저작권 고지와 MIT 라이선스 문구를 유지해야 합니다. 제3자 기반 자료는 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md), 번들에 포함되지 않은 외부 이미지·폰트·브랜드 자산은 각 원저작자의 라이선스와 사용 조건을 따릅니다.
