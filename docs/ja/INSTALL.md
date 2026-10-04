# インストール

ランタイムのインストール後、**`Prepare models now? [Y/n]`** と表示されます。Enter または Y でモデル準備を実行し、N で省略します。Y を選ぶ前にキャッシュを設定してください。対話端末がない場合や `--json` 使用時は既定で省略します。自動化では `--prepare-models` または `--skip-models` を指定できます。後から `clef-use models prepare` を実行することもできます。

venv/pip を含む Python 3.11-3.13 をインストールしてください。モデル準備には Python 3.11 と Git が必要です。root や管理者権限は不要です。ダウンロード URL を使う前に公開配備の検証結果を確認してください。

```sh
curl -fsSL https://ftp.kotori9.dev/clef-use/install.sh | sh
```

```powershell
irm https://ftp.kotori9.dev/clef-use/install.ps1 | iex
```

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

削除時は待機中のランタイムを停止し、管理された実行ファイルとディレクトリだけを削除します。POSIX は ~/.local/bin/clef-use と ~/.local/share/clef-use、Windows は %LOCALAPPDATA%\clef-use と対応するユーザー PATH 項目です。harness では clef-use 項目だけを削除します。明示的に消したい場合を除きキャッシュと設定を残してください。

[Quick start](QUICKSTART.md) | [Harness](HARNESS_SETUP.md) | [Evidence](../evidence/VALIDATION.md)

0.1.8の `models prepare` はWindows Radeon 890M (gfx1150)で固定ROCm/NF4構成を自動選択します。Python 3.12とCPU OmniParserを使用し、両方のモデルを初期化してから設定を保存します。明示的な変更は `--profile default` または `--quantization none` を指定してください。検証対象は一つの一時GUIタスクで、公開配布は別途確認します。

`models prepare` は9段階の準備状況、バックエンドとキャッシュ、現在の依存関係やモデル、キャッシュの再利用、経過時間を表示します。長い処理中は10秒ごとに状態を表示します。段階数は全体の所要時間の割合ではありません。`models prepare --json` で段階表示を抑制できます。設定は両方のモデルの初期化が成功した後に保存されます。
