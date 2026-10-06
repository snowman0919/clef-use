# インストール

ランタイムのインストール後、**`Prepare models now? [Y/n]`** と表示されます。Enter または Y でモデル準備を実行し、N で省略します。Y を選ぶ前にキャッシュを設定してください。対話端末がない場合や `--json` 使用時は既定で省略します。自動化では `--prepare-models` または `--skip-models` を指定できます。後から `clef-use models prepare` を実行することもできます。

venv/pip を含む Python 3.11-3.13 をインストールしてください。モデル準備には Python 3.11/3.12 と Git が必要です（Windows ROCm は 3.12 が必要）。root や管理者権限は不要です。ダウンロード URL を使う前に公開配備の検証結果を確認してください。

```sh
curl -fsSL https://ftp.kotori9.dev/clef-use/install.sh | sh
```

```powershell
irm https://ftp.kotori9.dev/clef-use/install.ps1 | iex
```

更新では以前のランタイム、モデルキャッシュ、設定を保持します。有効化前に Ctrl-C で
中断すると、後処理は未使用の一時環境だけを削除し、既存のランタイムは有効なままです。
原子的な切り替え後は、成功メッセージが出ていなくても新しい有効環境を保持します。
インストーラーを再実行して有効なバージョンを確認してください。強制終了や停電では
後処理が実行されず、一時ファイルが残る場合があります。クラッシュ時の永続性と
残存ファイルの自動削除は保証しません。

~/.config/clef-use/config.toml を作成するか CLEF_USE_CONFIG を指定します。model_dir を書き込み可能なキャッシュに変更してください。最低 30 GiB の空き容量と約 19.1 GB の CLEF-Flash 重みを処理するメモリが必要です。今回の環境はメモリ 48 GiB です。完全版 CLEF の重みは約 55 GB で、ここでは未検証です。

```toml
model_dir = "/path/to/external-ssd/clef-use/models"
device = "auto"
parser_device = "cpu"
max_steps = 30
confidence_threshold = 0.55
```

models prepare はバージョン固定の独立 ML 環境を二つ作り、公式 snapshot を取得します。更新時もキャッシュを維持します。Python 3.11 が見つからない場合は --python に実行ファイルの絶対パスを指定してください。

```sh
clef-use models prepare --python python3.11
clef-use doctor
clef-use install-mcp codex
clef-use install-mcp hermes
clef-use install-mcp omp
clef-use run 'In the open Calculator, compute 123 * 456' --success 'Calculator shows 56088'
clef-use status
clef-use abort
clef-use update
```

macOS では実際のターミナルまたは harness に画面収録とアクセシビリティ権限を与え、再起動します。Linux はアクセス可能なグラフィカル画面が必要で、Wayland ではキャプチャと入力が制限される場合があります。Windows のパッケージングは CI 対象ですが、実際の ML/GUI 互換性は実験段階です。加速検出だけではモデル動作の証明になりません。

doctor が失敗したら、権限、snapshot 不足、ML 依存関係、MCP 起動エラーを区別してください。self-test はモデルなしで制御フローを確認します。対応 Python が見つからなければ CLEF_USE_PYTHON を指定します。LOW_CONFIDENCE と NEEDS_REPLAN は計画側の介入要求で、ERROR は完了ではありません。

インストールディレクトリ全体を削除せず、`clef-use uninstall` で管理されたランタイムを
削除してください。既定の場所は POSIX の `~/.local/share/clef-use` と
`~/.local/bin/clef-use`、Windows の `%LOCALAPPDATA%\clef-use` です。ディレクトリには
保持すべきユーザーデータも含まれる場合があります。登録も削除する場合に限り、harness
設定や PATH から clef-use の項目だけを手動で削除します。uninstall はこれらを変更しません。

[Quick start](QUICKSTART.md) | [Harness](HARNESS_SETUP.md) | [Evidence](../evidence/VALIDATION.md)

0.1.8の `models prepare` はWindows Radeon 890M (gfx1150)で固定ROCm/NF4構成を自動選択します。Python 3.12とCPU OmniParserを使用し、両方のモデルを初期化してから設定を保存します。明示的な変更は `--profile default` または `--quantization none` を指定してください。検証対象は一つの一時GUIタスクで、公開配布は別途確認します。

`models prepare` は9段階の準備状況、バックエンドとキャッシュ、現在の依存関係やモデル、キャッシュの再利用、経過時間を表示します。長い処理中は10秒ごとに状態を表示します。段階数は全体の所要時間の割合ではありません。`models prepare --json` で段階表示を抑制できます。設定は両方のモデルの初期化が成功した後に保存されます。

## 修復と削除

```sh
clef-use doctor --fix
clef-use uninstall
```

`doctor --fix` は診断後、不足したモデルと推論依存関係を既存の準備処理で修復し、再診断します。
`docker --fix` は同じコマンドの別名です。変更されたソース、OS 権限、画面接続は手動対応を
案内し、自動上書きしません。ランタイムの停止が必要な修復・削除は、実行中のタスクや
モデル hold がある場合に拒否します。`uninstall` は待機中のランタイムを停止し、管理された
ランチャーとランタイムのバージョンだけを削除します。モデルキャッシュ、推論環境、設定、
MCP 登録、PATH は保持し、インストールルート全体は削除しません。Windows ではコマンド
終了後の削除を予約します。完了と判断する前に、`result` が指定する JSON ファイルの
`UNINSTALLED` または `ERROR` を確認してください。
