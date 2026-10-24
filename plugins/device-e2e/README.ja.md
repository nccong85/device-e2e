[English](README.md) · [Tiếng Việt](README.vi.md) · **日本語**

# device-e2e

Mac から実機でモバイルアプリのエンドツーエンドテスト (E2E テスト) を自動化するプラグインです。iPhone は
WebDriverAgent、Android は adb + uiautomator で操作します。

## 構成

| 構成要素 | 役割 |
|---|---|
| `agents/device-tester.md` | **メインの実行エージェント:** テストケースの作成、スマートフォンの操作、失敗原因の切り分け (ツールかアプリか)、テスト後の後片付け、証拠 (evidence) 付きの結果レポート (PASS/FAIL/BLOCKED) を担当します。*注意: アプリのコードを変更するのは brief で指示された場合だけです。* |
| `skills/playbook/` | **手順書と参照ドキュメント:** 実行手順、失敗の分類方法、実機の扱い方のルール、レポートの書き方。参照ドキュメント (`references/`) 付き: テストケースの設計方法、各ステータス (PASS/FAIL/...) を定義する用語集、iOS/Android 別のドキュメント、よくある落とし穴 (traps) の一覧。 |
| `skills/playbook/e2e_test_plan.template.md` | **テスト計画 (Test Plan) テンプレート:** 入力、リスク評価、状態/イベントのマトリクス、実行ステップ、ケースごとの時間予算を書く標準形式。結果ファイルのテンプレートと不具合記録の形式 (`BUG-n`) も含みます。 |
| `bin/validate_e2e_plan.py` | **テスト計画チェッカー:** AI モデルなしで単独で動き、テスト計画をクロスチェックします。すべての要求 (spec) がカバーされていること (または除外の理由が明記されていること)、冗長なケースがないこと、状態の抜けがないこと、合計実行時間が上限内であることを確認します。`--results` を付けると、実際の結果ファイルを計画と突き合わせます (証拠が実在するか、バグ記録に必要な情報がそろっているか)。 |
| `skills/playbook/harness/` | **デバイスドライバー:** `IosDriver` (WebDriverAgent への HTTP 呼び出し) と `AndroidDriver` (adb + uiautomator) は同じメソッド構成です。`evidence.py` は証跡ファイル (スクリーンショット、UI ツリー、logcat または iOS のクラッシュレポート、Android の画面録画) を命名して保存します。環境変数で設定でき (`WDA` は iPhone の IP、`E2E_*` はその他の設定)、Python 3 標準ライブラリのみを使います。 |
| `commands/init.md` | `/device-e2e:init` コマンド。テンプレートから設定ファイル `.claude/device-e2e/project.md` を作成し、まだ記入が必要な項目を一覧表示します。 |
| `skills/playbook/project.template.md` | **プロジェクト設定テンプレート:** エージェントの実行に必要な情報 (デバイス情報、アプリ ID、ビルドコマンド、ハーネスのパス、データの後片付け方法) を記入します。 |

## セットアップ

1. **プラグインのインストール:** `claude plugin marketplace add nccong85/device-e2e` を実行し、続けて
   `claude plugin install device-e2e@device-e2e` を実行します。*(推奨: [escanner-agent-kit](https://github.com/nccong85/escanner-agent-kit)
   の `review-gate` プラグインも入れてください。そのフックが、データを壊す git コマンドをエージェントが実行するのを防ぎます。)*
2. **プロジェクトの初期化:** プロジェクトのフォルダで `/device-e2e:init` を実行します。設定ファイル
   `.claude/device-e2e/project.md` を作成し (既存のファイルは上書きしません)、不足している情報の記入を促します。
3. **実機の準備:**
   - **iPhone:** WebDriverAgent を一度だけ実機にビルドし、Developer Mode と UI Automation を有効にします。iPhone
     はロックを解除したままにし、Mac と同じ Wi-Fi に接続しておきます。
   - **Android:** ケーブルを接続し、ホスト (Mac、Linux、Windows。iOS は Mac が必要) がデバイスを認識していることを確認します (`adb devices` で確認)。

   詳細: [`ios.md`](skills/playbook/references/ios.md)、[`android.md`](skills/playbook/references/android.md)。
4. **スイートの作成:** 2 つのドライバーの上に、アプリのフローモジュールとスイートを書きます。形はスキルが説明しています。

## 使い方

### 呼び出しの仕組み

プラグインは 3 つの部分からなり、Claude Code はそれぞれを別の方法で呼び出します:

| 部分 | 呼び出し方 |
|---|---|
| スキル `playbook` | 依頼がスキルの説明 (実機でのテスト、実機での e2e/回帰テスト、ハードウェアでの修正確認など) に合うと Claude が自動で読み込みます。直接呼ぶ場合は `/device-e2e:playbook`。 |
| エージェント `device-tester` | 依頼がエージェントの説明に合うと、メインのセッションが作業を任せます。名前で頼む (「device-tester エージェントで…」) か、`@agent-device-e2e:device-tester` と入力します。エージェントは起動時に `playbook` スキルを読み込みます。 |
| コマンド `/device-e2e:init` | 入力したときだけ実行されます。 |

依頼の書き方を決める点が 2 つあります:

- **エージェントは会話の履歴を見ません。** 独立したコンテキストで動き、メインのセッションがあなたの依頼から書いた
  brief だけを受け取ります。必要な情報 (spec、plan、プラットフォーム、予算、承認済みの事項) はすべて依頼文に入れてください。
- **エージェントはあなたに質問できません。** 情報や承認が足りないと `BLOCKED: …` で止まります。メインのセッションが
  それを伝えるので、次の依頼を送ってください。

### brief

エージェントは次の固定行を受け取ります:

```
SPEC: <spec のパス>
PLAN: <plan のパス> | write (MODE: feature | release)
PLAN_APPROVED: <承認者, YYYY-MM-DD> | none
BUILD: installed | approved <承認者, YYYY-MM-DD>
PLATFORMS: ios, android | ios | android
CASES: all | <ID>
BUDGET: <実機の使用時間 (分)>
RESULTS: <結果ファイルのパス> (既定: project.md のパス)
```

`SPEC`、`PLAN`、`PLATFORMS`、`BUDGET` のいずれかが無いと、エージェントは `BLOCKED: brief missing <field>` で止まります。
承認は brief に書かれたものだけが有効です。plan ファイル内の *Approved by* 行は数えません。

### 2 回に分けて実行

**1 回目: plan の作成。** エージェントは plan を書き、`validate_e2e_plan.py` がエラーなしで終わるまで直し、実機に触れる前に
`BLOCKED: plan <path> needs owner approval` で止まります。

> device-tester エージェントで: SPEC docs/specs/import_pdf.md, PLAN write (MODE: feature), PLAN_APPROVED none,
> BUILD installed, PLATFORMS ios, android, CASES all, BUDGET 60.

**レビュー。** plan (ケース、実機の使用時間、*Not covered*) を読み、必要なら修正します。

**2 回目: 実行。** エージェントは `READY` → `DRY` → 順番どおりのケース → `EXPLORE` (計画にある場合) → `DIAG` を実行し、すべての FAIL を切り分け
(ハーネスのバグは直して再実行、アプリのバグは証拠を集める)、後片付けをして結果ファイルを書きます。

> device-tester エージェントで: SPEC docs/specs/import_pdf.md, PLAN test/e2e/import_pdf_plan.md,
> PLAN_APPROVED nccong 2026-10-24, BUILD installed, PLATFORMS ios, android, CASES all, BUDGET 60.

エージェントは最後に次の 4 行を返します:

```
E2E: ios pass=<n> fail=<n> blocked=<n> not_run=<n> · android pass=<n> fail=<n> blocked=<n> not_run=<n>
APP_BUGS: <none | BUG-n 重大度 タイトル>
BLOCKERS: <none | ケースや実行を止めたもの>
REPORT: <結果ファイルのパス>
```

よくある依頼: 失敗したケースだけ再実行 (`CASES: E3, E7`)、片方のプラットフォームだけ (`PLATFORMS: android`)、
再ビルドを許可 (`BUILD: approved nccong 2026-10-24`、`project.md` のビルドコマンドを使用)。

「実機 2 台で PDF のインポートをテストして、spec は docs/specs/import_pdf.md、60 分」のような短い依頼でも動きます。
メインのセッションが brief を組み立てますが、足りない行があればエージェントは `BLOCKED` を返します。

## やらないこと

- brief にオーナーの承認が書かれていない限り、アプリをビルドまたは再インストールしません。アンインストールするとアプリのデータが消えます。
- データが重要なスマートフォンで `xcodebuild test` や `flutter drive` を使いません。
- 実機から読み取った証拠なしに、または前提条件が証明されていないケースについて、PASS を報告しません。
- オーナーがテスト計画を承認する前に実機を動かしたり、計画したケースを結果から削除したりしません。
