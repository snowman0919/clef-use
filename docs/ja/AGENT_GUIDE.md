# エージェントの設定・使用・復旧

runtime wheel には指示専用の共通スキル `clef-use`、`clef-use-blender`、
`clef-use-diagnostics` が含まれます。既定は core と diagnostics で、Blender は
明示的に選択します。適用前に変更先のパスを確認してください。選択した対象だけ
変更します。初回の無人インストールは `--integrate codex|hermes|omp|all` なしに
新しいハーネスを登録しません。モデルの準備は別の選択です。

OMP の `PI_CONFIG_DIR` は HOME からの相対パス名で、既定は `.omp` です。
絶対パスの既定 agent ディレクトリには `PI_CODING_AGENT_DIR` を使います。
空または `default` の `OMP_PROFILE` は `PI_PROFILE` より優先して既定 profile を選択します。

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
しません。live 検証は実際のハーネスの新しいセッションで読み取り専用ツールを
使用します。provider 認証の失敗時、ロードと呼び出しは `NOT_RUN` のままです。

`MODIFIED`・`CONFLICT` はユーザーの編集を保存し、統合状態ディレクトリに比較用
コピーを残します。明示的に無効にした項目は有効にしません。更新後は capability
のバージョンを確認し、キャッシュされたクライアントを再ロードしてください。
削除するのは変更されていない管理項目だけです。Hermes は project scope 非対応
なので、選択した user profile を使います。移動前に source・shadow を確認します。

自分のセッションだけ中止し、入力の解放を確認してください。正確な Unicode
clipboard 入力と IME の変換は別です。IME が有効または不明ならショートカットを
遮断します。watchdog 復旧は OS 権限と確認の時間窓に制約されます。
現在、測定で合格した 100ms profile や出荷 gate の成功は主張していません。
[実行証拠](../EXECUTION_STATUS.md)と[検証項目](../../ACCEPTANCE.yaml)を参照してください。
