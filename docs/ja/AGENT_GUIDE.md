# エージェントの設定・使用・復旧

runtime wheel には指示専用の共通スキル `clef-use`、`clef-use-blender`、
`clef-use-diagnostics` が含まれます。既定は core と diagnostics で、Blender は
明示的に選択します。適用前に変更先のパスを確認してください。選択した対象だけ
変更します。初回の無人インストールは `--integrate codex|hermes|omp|all` なしに
新しいハーネスを登録しません。モデルの準備は別の選択です。

編集だけでなく、読み取り専用のメニュー・状態評価にも Blender スキルをロードします。
`references/` ファイルは元のスキルに属します。Hermes では
`skill_view(name="clef-use", file_path="references/API_BASELINE.md")` で基準 API を読みます。

OMP の `PI_CONFIG_DIR` は HOME からの相対パス名で、既定は `.omp` です。
絶対パスの既定 agent ディレクトリには `PI_CODING_AGENT_DIR` を使います。
空または `default` の `OMP_PROFILE` は `PI_PROFILE` より優先して既定 profile を選択します。

登録先が固定された旧インストール先の場合、`refresh` はその実行パスを保持し、
新しいガイドとの不一致を拒否します。`--command-path` も既存登録を上書きしません。
まず管理対象の削除を `--dry-run` で確認し、未変更の管理対象だけを削除してから、
現在の実行ファイルを `--command-path` で登録してください。ユーザーの編集や
無効化された項目との競合は保持されます。

<!-- clef-use:commands -->
operation の `SUCCEEDED` は型付き効果の検証です。自然言語の目標には別の fresh
`ASSESS` が必要なため、セッションは `NEEDS_REPLAN` を返します。ハーネス検証の
`--trigger natural|explicit|negative|native` でモデル起動と native adapter を区別します。

```sh
clef-use capabilities --json
clef-use capabilities --detail --json
clef-use capabilities --operation-id numeric_transform --json
clef-use integrate codex --dry-run
clef-use integrate codex --scope user --skills core --skills blender --skills diagnostics
clef-use integrate hermes --scope user
clef-use integrate omp --scope user
clef-use integrations status --json
clef-use integrations verify codex --live --read-only
clef-use integrations remove codex --dry-run
clef-use integrations refresh --managed-only
```

現在の schema を確認し、検証できる小さな目標を送信します。文字列を正確に指定し、
文字入力とショートカットを区別してください。keymap を推測しないでください。
`ASSESS` は入力しません。過去の観測は新しい pointer の許可や最終完了の証拠に
なりません。ローカル operation は型付き有限状態手順で、Agent Skill の自然言語
指示とは別です。信頼できるローカル観測器による editor・selection・mode・IME・
keymap の確認が必要です。不明な状態は入力を遮断します。既定の screenshot
観測器は Blender の隠れた状態を断定できません。API 補助 fixture の成功は
pixels-only 操作の成功を証明しません。

既定のインストールは screenshot と取得可能な native window identity を使います。
信頼できる Blender application provider と公開 provider 設定経路は含みません。
必要な検証済み状態がないため、登録された六つの operation はすべて `BLOCKED`
を返します。discovery は実装済み schema と既定環境の実行可否を分け、実際の
`READY` 状態を主張しません。検証済みなのは制御された `API_ASSISTED` Blender
fixture の手順です。一般的な production provider は未完了の要件です。
不明な focus・IME・popup 状態を仮定で置き換えないでください。

typed operation セッションの継続には明示的な `operation` が必要です
(`clef-use continue ... --operation '<JSON>'`)。planner の指示だけでは直前の効果を
繰り返しません。元の目標全体の検証には `operation` を指定せず、
`execution_mode="ASSESS"` の新しい `computer_run` 契約を作成します。CLI では
`clef-use run "Verify the complete original goal" --mode ASSESS` を使います。

`INSTALLED`、`DISCOVERED`、`LOADED`、`INVOKED`、`TASK_VERIFIED` を別々に記録
します。ファイルのコピー、ツール一覧、スキル名の応答だけでは次の段階を通過
しません。live trigger 検証は実際のハーネスの新しいセッションで読み取り専用ツールを
使用します。provider 認証の失敗時、ロードと呼び出しは `NOT_RUN` のままです。
作業の検証には、隔離した対象への許可済み入力、外部からの新しい状態確認、
入力とプロセスの終了確認が別途必要です。非公開 API 補助作業の成功は、
production での実行可能性や目標全体の完了を証明しません。

`MODIFIED`・`CONFLICT` はユーザーの編集を保存し、統合状態ディレクトリに比較用
コピーを残します。明示的に無効にした項目は有効にしません。更新後は capability
のバージョンを確認し、キャッシュされたクライアントを再ロードしてください。
削除するのは変更されていない管理項目だけです。Hermes は project scope 非対応
なので、選択した user profile を使います。移動前に source・shadow を確認します。

ローカル要求は実行ファイルのバージョン、runtime protocol、API 指紋に結び付きます。
古いクライアントは新しいサービスを停止・操作できません。不一致時は現在の
実行ファイルと MCP セッションを再ロードしてください。新しいクライアントは
待機中の古いサービスを置換できますが、入力実行や modal 復旧中は置換しません。
更新前から実行中のセッションは、保存された同じバージョンの実行ファイルで
完了または中止してください。不変の旧クライアントはサーバーの再ロード案内を
表示せず、一般的な拒否だけを返す場合があります。同じバージョンの protocol・
schema が違う場合、待機中のサービスを明示的に停止してから再ロードします。
自動的に再起動することはありません。

自分のセッションだけ中止し、入力の解放を確認してください。正確な Unicode
clipboard 入力と IME の変換は別です。IME が有効または不明ならショートカットを
遮断します。watchdog 復旧は OS 権限と確認の時間窓に制約されます。
X11 の文字入力は ASCII も明示的な clipboard 方式を使います。キーイベントは
変換開始前でも IME に渡る場合があります。転送確認と入力欄の結果確認は別です。
既存 clipboard 形式を保存できない場合は入力前に拒否します。受信前に中止した
場合、既に送られた貼り付け用の文字を転送完了または別のコピーまで維持し、以前の
データを早く復元しません。Windows 操作は native Unicode を使います。
decision 診断には画像を除く実際の UTF-8 テキスト予算のバイト数、object・question
数、SDK が報告した入力トークン数を保持します。`SDK_USAGE` は 1～8192 の整数、
欠落は `UNAVAILABLE`、不正な報告値は `INVALID` とし、後二者の数は null です。
これらは正しい対象の coverage、校正された信頼度、モデル遅延の測定ではありません。
全機会の事前適格性・policy 証拠がなければ、反応 coverage は null・`NOT_MEASURED`
のままです。高速な成功入力だけでは出荷 gate を通過しません。実際の OS event
時刻と backend ACK は区別します。
現在、測定で合格した 100ms profile や出荷 gate の成功は主張していません。
[実行証拠](../EXECUTION_STATUS.md)と[検証項目](../../ACCEPTANCE.yaml)を参照してください。
