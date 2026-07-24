<p align="center">
  <img src="assets/readme-hero.svg" alt="Codex、Claude Code、Gemini CLI向け Build HTML Slides" width="100%" />
</p>

<p align="center">
  <a href="https://github.com/mclub4/build-html-ppt/releases"><img alt="Release" src="https://img.shields.io/github/v/release/mclub4/build-html-ppt?color=f06b52" /></a>
  <a href="LICENSE"><img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-57c7b6" /></a>
  <img alt="Codex, Claude Code, and Gemini CLI" src="https://img.shields.io/badge/support-Codex%20%2B%20Claude%20Code%20%2B%20Gemini%20CLI-20252b" />
</p>

<p align="center">
  <a href="README.md">한국어</a> · <a href="README.en.md">English</a> · <strong>日本語</strong>
</p>

<h1 align="center">Build HTML Slides</h1>

<p align="center">
  Codex、Claude Code、Gemini CLIが、発表相手・目的・根拠資料を踏まえてHTMLスライドと発表者ノートを制作するためのプレゼンテーションスキルです。
</p>

<h2 align="center">
  <a href="https://html-ppt-gallery.unequaled-condor.workers.dev/">Build HTML Slidesで制作した作品を見る</a>
</h2>

<p align="center">
  <a href="https://html-ppt-gallery.unequaled-condor.workers.dev/">
    <img src="assets/gallery-preview.webp" alt="Build HTML Slides ギャラリー" width="100%" />
  </a>
</p>

> OpenAI Codex CLI / Codex App、Anthropic Claude Code、Google Gemini CLIに対応しています。本リポジトリはコミュニティープロジェクトであり、各プラットフォーム提供会社の公式プロジェクトではありません。

## 現在の状態と制作モード

本スキルは試験運用中です。デスクトップでの発表を優先しており、モバイル対応を明示的に依頼して検証していない資料では、小さい画面での表示を保証しません。

- **Quick Draft:** HTML、ローカル素材、`sources.json`、Markdown形式の発表者ノートを作成してすぐに納品します。ブラウザー描画や視覚検証は行いません。
- **Full Validation:** 全スライドを描画し、配置・文字・画像・操作を自動検査したうえで、フルサイズPNGをAIレビューに回し、最後に独立した品質レビューを1回行います。

約15枚では、Codex GPT-5.6・推論強度Mediumを基準に、Quick Draftは約10分、Full Validationは約1時間を目標とします。20〜25枚のFull Validationは40〜90分が目安です。調査量、画像探索、モデル、実行環境によって変動します。

## 生成物

- オフラインで開ける単一HTMLプレゼンテーション
- 話す内容、強調点、遷移、出典上の注意を含む `OUTPUT-notes.md`
- ローカルWebP画像と編集可能なSVG図
- URL、ハッシュ、出典種別、確認日、クレジットを記録する `sources.json`
- キーボード、クリック、ページ番号入力、フルスクリーン、ハッシュ、印刷対応
- `visualViewport`を基準に安全に拡大縮小する1280×720固定ステージ

## 聴衆を考慮したデザイン推論

主題の単語をそのままテーマへ変換しません。次の要素を組み合わせます。

1. 12種類の大分類から選ぶ主題領域と、その領域で必要な証拠
2. 紹介、教育、意思決定、発売、研究共有、障害振り返り、ロードマップ、比較など10種類の発表目的
3. 実際の聴衆、会場で得たい結果、利用可能な実写資料、使用言語
4. 情報密度、実写必要度、視覚的な冒険度、モーションを1〜10で表した内部調整値

その後、性格の異なるデザイン候補を3案検索し、少なくとも1案を具体的な理由とともに却下します。最高スコアは自動採用ではありません。主題領域が固定するのは証拠の条件であり、色・書体・明るさではありません。そのため「技術」というだけで暗いコンソール風にはなりません。

候補には、Paper Systems、Constructive Geometry、Organic Systems、Scholarly Review、Archival Analog、Editorial Grid、Documentary Photo Essay、Product Keynote、Scientific Atlasなどがあります。Kinetic Typography、Exaggerated Minimalism、3D Product Evidence、Parallaxは全編テーマではなく、表紙や章扉などに限定する補助表現です。

グラフも主題ではなくデータ形状から選びます。使用条件、避ける条件、カテゴリー数の上限、色以外の区別方法を機械可読データとして保持します。

## Full ValidationとSquint review

Full Validationでは、通常画面、低い画面、Chromiumの実際の150%ページズームを撮影します。AIレビューの前に、文字境界、フォント整合性、低情報量の大きな箱、操作UI、画像比率、プレースホルダー、出典、発表者ノート、ブラウザー操作を自動検査します。

修正が完了した後、既存の`normal` PNGだけを再利用して、縮小と弱いぼかしを加えた **squint contact sheet** を1枚生成します。独立した品質編集者は次の4点だけを確認します。

- 最初に目に入る要素が明確か
- 重要度の強弱があるか
- 全体のリズムが単調でないか
- 色と情報密度のバランスが自然か

Squint reviewは安価な補助検査です。文字の重なり、不自然な改行、切り抜き、変形、はみ出し、人物・キャラクターの一致、画像内容の妥当性は判定できません。これらはフルサイズ画像で確認します。Squint画像は全`normal`キャプチャーのハッシュに結び付けられ、スライドの再描画は行いません。

## 必要環境

- Codex CLI / App、Claude Code、またはGemini CLI
- Python 3.10以上
- Node.js 18以上
- Full Validationの場合のみPlaywrightとChromium

リポジトリで開発・検証する場合:

```bash
npm install
npx playwright install chromium
npm run check:browser
```

Quick Draftはブラウザー依存を確認・導入しません。Full Validationは非破壊の事前検査を実行し、不足ツールはユーザーの明示的な同意後にのみ導入します。

```bash
python3 <installed-skill>/scripts/install_browser_dependencies.py --consent
```

## インストール

同じプラットフォームでは、プラグイン版か単独スキル版のどちらか一方を選んでください。両方を入れるとスキルが重複表示される場合があります。

### Claude Codeプラグイン

```bash
claude plugin marketplace add mclub4/build-html-ppt
claude plugin install build-html-slides@build-html-slides
```

### Codexプラグイン

```bash
codex plugin marketplace add mclub4/build-html-ppt
codex plugin add build-html-slides@build-html-slides
```

### Gemini CLI Agent Skill

`.skill`ファイルは[GitHub Releases](https://github.com/mclub4/build-html-ppt/releases)の添付ファイルです。`dist/`はgitignore対象でリポジトリには含まれないため、まずReleasesから取得するか、`./scripts/package-release.sh`でローカル生成してください。

```bash
gemini skills install ./BUILD-HTML-SLIDES-GEMINI-vX.Y.Z.skill
gemini skills install ./ARCHIFY-GEMINI-v2.12.0.skill
gemini skills list
```

### リポジトリから単独インストール

```bash
git clone https://github.com/mclub4/build-html-ppt.git
cd build-html-ppt
./install.sh
```

インストール後はAIエージェントのセッションを再起動してください。

## AIエージェントがインストールした場合

インストール担当エージェントは、次の点を必ず説明します。

- [`epoko77-ai/im-not-ai`](https://github.com/epoko77-ai/im-not-ai) は韓国語文章を整える任意の補助スキルであり、本リポジトリには同梱されません。
- 本リポジトリは[`tt-a1i/archify`](https://github.com/tt-a1i/archify)のArchify v2.12.0を同梱し、アーキテクチャ、トポロジー、シーケンス、ワークフロー、ライフサイクル、データフロー図向けの独立スキルとして提供します。
- 利用可能な`humanize-korean`と同梱された`archify`は、適用条件に合えば再確認なしで利用します。別途導入済みのArchifyは`--force`を明示しない限り上書きしません。
- Claude Codeには標準でラスター画像生成機能がないため、生成画像には互換プラグイン、MCP、または外部ツールが別途必要です。
- 任意スキル、画像生成サービス、認証情報は同意なしに導入・設定しません。追加導入を確認する対象は、未導入の`humanize-korean`だけです。

## 使い方

インストール後は自然文で依頼できます。

```text
経営陣、事業チーム、開発チーム向けに12枚のHTMLプレゼンを作ってください。
意思決定と現状の影響を技術詳細より先に置いてください。
最初にQuick DraftとFull Validationを提示し、私が選ぶまで待ってください。
```

Full Validationの入口は1つです。

```bash
python3 scripts/validate_all.py OUTPUT.html --mode full --phase prepare
python3 scripts/validate_all.py OUTPUT.html --phase verify
python3 scripts/validate_all.py OUTPUT.html --phase finalize-prepare
python3 scripts/validate_all.py OUTPUT.html --phase finalize-verify
```

検証ファイルは既定で成果物フォルダーの外に保存されます。

```text
~/.codex/build-html-slides/workspaces/<presentation-id>/
~/.claude/build-html-slides/workspaces/<presentation-id>/
~/.gemini/build-html-slides/workspaces/<presentation-id>/
```

## 開発

```bash
npm test
npm run test:e2e
npm run check
```

正本は`codex/skills/build-html-slides`です。`scripts/sync-distributions.sh`でCodexプラグイン、Claude Code、Gemini CLI向け配布物を同期します。

## ライセンス

MITライセンスです。[LICENSE](LICENSE)を参照してください。リポジトリに含まれる第三者由来部分は[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)に記載しています。今回追加したデザイン候補インデックスと推薦スクリプトは本プロジェクト独自のものであり、外部のスタイル、配色、フォント、製品分類データセットは同梱していません。
