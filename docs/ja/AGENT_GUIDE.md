# エージェントの設定・使用・復旧

不変の .52 CI は15個の実際のビルド・インストールと結合に成功しました。
全15アーカイブのソース・ガイド68ファイルと契約が固定 Git コミットに一致します。
実際のログは初回・更新・CURRENT と checksum/download/smoke 失敗時の保持を示します。
合成更新 fixture の最終版は .53、実際の候補は .52 です。公開配備は feature guard
でスキップされます。Windows .52 のインストールと LIMITED CLI/MCP は NOT_RUN です。
SSH port22 と Tailscale ping がタイムアウトし、ローカルは online ですが win peer は
offline と表示されます。原因は未証明です。以前の共有 .49・専用 .51 の結果は今回
再検証していません。別の Windows 操作セッションも確認済みで、入力の調整が必要です。
[.52 CI・接続記録](../validation/2026-10-14/ci-and-windows-transport-0152.json)を参照してください。

.52 の `computer_capabilities.operation_id` は登録済み family ID を広告します。
まず引数を省略して取得し、`operations[].family` から選んでください。`blender` などの
アプリ名は引き続き拒否します。実パッケージの通常/読み取り専用 MCP 検査は合格です。
Hermes の3件は合格、OMP の肯定ケースはガイド順序・期限・書き込み拒否で失敗し、
非関連ケースは合格しました。OMP 認証関連 DB 行の変化の原因・認証値差分は未証明で、
復元していません。[.52 記録](../validation/2026-10-14/operation-schema-0152.json)を参照。
この時点の Windows .52 と GUI/性能は NOT_RUN です。
OMP 読み取り専用検証は、`--tools` 外へ強制追加される自動学習 writer と案内を
一時設定で無効化し、保存済み設定を保持します。実 SDK 構成検査は合格しましたが、
修正後も明示ケースの status・書き込み・期限と自然言語ケースのガイド順序は失敗です。

不変の .51 CI で15件のネイティブインストール/パッケージ検査が合格しました。
Windows の独立 .51 は integration-preview なしで install/CURRENT が合格し、
共有 .49 と既存登録を保持しました。他のインストールのプロファイル更新は0件です。
LIMITED トークンの CLI/MCP と編集済み・別所有 launcher の拒否も合格しました。
タスクの不在は確認しましたが、SSH 制御の timeout 後の終了コードは取得できません。
別セッションが Windows を操作中のため、Codex .51、共有更新、GUI/性能は NOT_RUN
です。[.51 記録](../validation/2026-10-14/windows-isolated-ci-0151.json)を参照してください。

不変 .50 CI は 15 プラットフォームのインストール・アーカイブ検証に成功しました。
専用 Windows 候補は `--integration-preview` で CLI インストール、CURRENT、ファイルと
LIMITED トークンの MCP 検証に成功しました。別セッションが Windows を操作中のため、
共有 .49 と有効なハーネス登録を保持します。標準更新、native Codex .50、GUI E2E は
NOT_RUN です。[候補検証記録](../validation/2026-10-14/windows-isolated-ci-0150.json)を参照してください。

OMP は読み取り専用 MCP 呼び出しも `write xd://<tool>` で運びます。検証は native の
対象・引数・サーバー・結果と実際の利用側ペイロードが一致する場合だけ認定します。
メソッド名だけでファイル書き込みや安全な読み取りを判断しません。ガイド前の呼び出し、
実際に拒否された書き込み、不一致は引き続き失敗です。[ソース .50 記録](../validation/2026-10-14/omp-device-evidence-0150.json)では
native コンポーネント、保存 trace の再判定、新しいモデル実行を区別しています。

不変の .49 CI は 15 プラットフォームのインストール検証とアーカイブ・ソース照合に
成功しました。実際の Windows .48 -> .49 更新、再実行 CURRENT、LIMITED トークンの
パッケージ・MCP 検証と元の Codex explicit/natural/negative モデルケースも成功しました。
これらのウィンドウを使わない検証は GUI タスクや 100ms 入力遅延を証明しません。
以前の Hermes/OMP 失敗と公開配備のガードは維持します。
[インストール記録](../validation/2026-10-14/windows-installed-ci-0149.json)を参照してください。

runtime wheel には指示専用の共通スキル `clef-use`、`clef-use-blender`、
`clef-use-diagnostics` が含まれます。既定は core と diagnostics で、Blender は
明示的に選択します。適用前に変更先のパスを確認してください。選択した対象だけ
変更します。初回の無人インストールは `--integrate codex|hermes|omp|all` なしに
新しいハーネスを登録しません。モデルの準備は別の選択です。

読み取り専用検証では Hermes の native ツール定義 factory から `skill_manage` を
除外し、MCP 更新と遅延発見の一覧にも適用します。registry 実行も拒否します。
native Skill reader と元の schema は維持します。reader の使用 metadata は変わり得る
ため、ガイド・設定ファイルの保持を全 native 生成状態の保持とはみなしません。
OMP 検証は一時的な起動設定で実際の MCP 発見完了を待ちます。保存済み設定と
宣言されたモデル制限時間は変更しません。

実際の .48 専用 Linux 画面のキャッシュ検証は Windows インストール検証と分けます。
Hermes は実行限定の非公開読み取り専用制限の下で、キャッシュを完了証拠にせず、
新しい Continue 画面を確認しました。OMP の現在セッション既定値のキャッシュ項目は
成功しましたが、ガイド読み込み前の status 呼び出しにより native ケース全体は FAIL
です。実際の status/cache 読み取り後も明示的 ID の検証は失敗しています。OMP は
起動待機中にキャッシュのツール一覧を公開する場合があります。一時的な
`mcp.startupTimeoutMs: 0` は実際の発見完了を待ち、保存済み設定は変更しません。
これらの読み取り検証は GUI 入力精度や 100ms 遅延を証明しません。
[検証記録](../validation/2026-10-14/linux-native-cache-0148.json)を参照してください。

ハーネスの JSON ストリームは Windows locale に依存せず UTF-8 で読みます。
runtime 呼び出しの失敗は、後の capability 呼び出しが成功しても検証 FAIL のままです。
発見だけではモデルによるガイド読み込みやツール実行を証明しません。
ファイル読み込みと公開 guide resource は管理された本文全体と一致する必要があります。
capability の runtime/schema/guide hash と読み取り専用の二つのツールも確認します。
必要なガイドを呼び出し後に読む場合、検証順序は FAIL です。
先行する runtime 呼び出しの FAIL は、後のロード・成功・プロセス異常終了で消えません。
ネイティブ Skill catalog の発見は runtime 呼び出しと区別します。
operation 詳細応答は、先に検証した実際の一覧の該当 operation と完全一致する必要があります。
status 応答だけでは現在の capability 一覧を検証できません。

Codex のコマンド開始失敗は JSON command event がなく、非公開 stderr だけに
残る場合があります。ネイティブ runner pipe 接続のタイムアウトは、後の成功や
異常終了に関係なく `NATIVE_EXECUTOR_STARTUP_TIMEOUT` FAIL として保持します。
公開するのは段階、制限時間、ガイド読み込み試行の有無と証拠 hash だけです。
読み込み試行は本文ロードの証明ではなく、このエラーだけでは認証の問題や
ネイティブ実行器の失敗原因を特定できません。

MCP 接続の指示は、許可された GUI 作業または明示的な clef-use capability/schema
要求に適用します。通常のコード質問や runtime へのアクセスを禁じる要求では、
これらのツールを選択しません。読み取り専用接続は、実際に公開する
capability/status ツールと schema/guide resource を案内します。capability の
発見には実行中の GUI service は不要です。status は既存の service/session を
読み取り、Blender の隠れた状態を発見するツールではありません。
OMP のリンク先ファイルは
`read(path="skill://clef-use/references/API_BASELINE.md")` のように所有スキルの
ネイティブ reader で読みます。この URI を `file://` に変換しません。MCP resource
は実際の reader を発見してから使い、サーバー別名や resource のアドレスを推測しません。

OmniParser は upstream import 前後で呼び出し元の Torch thread 数を保持します。
明示的な単一 thread 設定も保持し、新しい thread 設定は不要です。
この初期化修正だけではタスク完了や 100ms の入力遅延を証明しません。
実際のインストール済み runtime で個別に検証してください。

編集だけでなく、読み取り専用のメニュー・状態評価にも Blender スキルをロードします。
`references/` ファイルは元のスキルに属します。Hermes では
`skill_view(name="clef-use", file_path="references/API_BASELINE.md")` で基準 API を読みます。
読み取り専用の GUI capability/schema 質問にも該当ガイドを使います。Skill catalog
を発見し、core と該当する Blender ガイドをロードしてから runtime ツールを呼びます。
入力を送らない capability 要求もツール呼び出しです。

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
指示とは別です。
検証済みの状態がある場合、guard はバージョン名だけでなく keymap の内容も比較します。
viewport ジェスチャーの前と途中に editor 領域を再確認し、変更時は停止して所有する入力を解放します。
view の基準も native ジェスチャーのボタン入力が確認されるまで保持します。それ以前の
独立した view 変化は成功に数えません。確認後の drag による変化は他の guard を保って許可します。
数値 transform には移動・回転・scale の XYZ 全成分の readback が必要です。
入力前に transform 文脈、開始前に初期値、commit 前に検証済み preview を再確認します。
一部の成分だけで他の軸の保持を判定しません。property 編集後は観測した全フィールドと
object ID を比較しますが、観測していないフィールドの保持までは確定しません。
数値 literal は要求された float を保持します。アプリの実際の readback も指定した
tolerance を満たす必要があります。
状態を変える operation と所有 modal の取り消しには、完全で安定した
`selection_identities` が必要です。Blender はプロセス範囲の公開 `session_uid` を
使います。改名しても ID は維持され、同名の別 object への置き換えは以後の入力を
遮断します。ID がない場合は UNKNOWN のままです。observer は位置と scale の
X/Y/Z 属性も提供します。使用前に operation registry v6 を確認してください。
数値移動は完全で新しい `scene_units` を要求し、入力・readback・所有 modal の取消まで
同じ scene 変換を保持します。単位名が同じでも scene の倍率は変わり得ます。
amount/readback は検証済み operation 単位を保ち、NONE は生の値です。変換の欠落や
変更は以後の入力・成功を遮断します。回転・scale に長さ設定は要求しません。
角度 readback は DEGREES/RADIANS の宣言と一致させ、exact-property 座標は生の値を保ちます。
位置の `property_edit.value` は Blender 単位の生座標です。新しい `scene_units`
根拠から明示的な meter 入力を計算し、入力と readback の間で固定します。不明または
変化した単位は入力・成功判定を止めます。scale は無次元です。表示単位による
生座標の再解釈は行わず、実際の readback は元の tolerance を満たす必要があります。
信頼できるローカル観測器による editor・selection・mode・IME・
keymap の確認が必要です。不明な状態は入力を遮断します。既定の screenshot
観測器は Blender の隠れた状態を断定できません。API 補助 fixture の成功は
pixels-only 操作の成功を証明しません。
キャプチャ由来の座標と foreground は取得時刻を保持します。取得や処理の遅延で
有効期間を更新せず、provider の独立した観測値は自身の時刻で判定します。
Windows の文字入力は送信前に UTF-16 を検証し、native 単位ごとに現在の guard を
再確認します。状態観測後にも取り消しと deadline を再確認します。X11 では paste
試行前の取り消しが確定した場合、所有 modifier を解放し、native ACK 後に対応する
元の clipboard 形式を復元します。同時に行われたコピーは保持します。paste が
届いた可能性があれば文字列を保持し、復元 ACK がなければ未解決として報告します。
legacy X11 キーボード入力も暗黙の Shift を含め、押す前に現在の binding を検証します。
キャッシュされた binding が変化すると入力を拒否します。解放には確認済みの物理
keycode を使い、外部ですでに押されているキーは解放しません。
Blender の view 効果は、完全で曖昧でない単一 viewport の実効 view matrix と
perspective mode で確認します。region・layout・projection だけの変化は orbit/pan
の証拠にせず、pose がない場合や quad view が曖昧な場合は UNKNOWN を保持します。

既定の provider は `NONE` です。screenshot と native window identity だけでは
Blender の隠れた状態を確定できません。Linux X11 と Windows では読み取り専用の Blender
observer を任意で設定できます。`clef-use blender-observer-script` が表示する
インストール済みパスを、許可済みの Blender 実行ファイルへ渡してください。
private な親ディレクトリの下に、まだ存在しない新しいディレクトリを指定します。
スクリプトが private ディレクトリと endpoint を作り、既存の Blender には自動接続しません。

```sh
clef-use blender-observer-script
blender --python "/absolute/installed/blender_observer.py" -- --clef-state-dir "/absolute/private/new-observer"
```

runtime の `config.toml` の最上位に設定します。既定の場所は
`~/.config/clef-use/config.toml` で、`CLEF_USE_CONFIG` で別のファイルを選べます。

```toml
blender_state_socket = '/absolute/private/new-observer/state.sock'
```

listener は Blender の最初の UI timer から起動します。Linux は Unix `SO_PEERCRED` と
XRes kernel process identity を確認します。Windows は明示的な `127.0.0.1` listener を
使い、`state.sock` は Unix socket ではなく private NTFS port metadata になります。
native TCP peer PID と process token user が foreground process に一致し、両 platform とも
唯一の RNA window/client の物理 pixel 寸法と変化していない native foreground を確認します。
UI timer が停止中なら provider は unavailable で、idle とは判定しません。
window・selection・object mode・生の transform/unit・
viewport・観測された modal operator を読み取り、scene の変更や operator の実行は
行いません。popup・text focus・IME・有効な keymap・全体の idle は不明のままです。
空の operator 一覧も不在の証拠にはなりません。この部分観測器を設定しても、必要な
検証済み状態がなければ六つの operation はすべて `BLOCKED` を返します。

観測器は所有 manager の公開 `interface_locked` Boolean を取得できる場合に保持します。
native identity・window・鮮度の検証を通過した `true` だけが、busy の陽性証拠として
`loading=true` になります。`false` や取得不能の場合は `loading` を UNKNOWN に保ちます。
解除後も modal や別の入力所有者が残り得るため、入力の許可や idle の判定には使いません。

`active_tool` は独立に関連付けた native context mode の VIEW_3D workspace tool と、
workspace・観測済み area ID を示します。欠落や曖昧さは UNKNOWN のままです。
focused editor と有効な dispatch も UNKNOWN で、この値だけでは入力を許可しません。
collector は初期化済み参照だけを読み、tool の作成・更新を行わず、128 個超を拒否します。

`keymap_inventory` は統合された user keymap の関連 binding、重複・無効項目、
tri-state modifier（`-1` は any）、内容 digest を保持する生の一覧です。
有効な dispatch を示す `keymap` や `keymap_version` ではありません。
`editor_layout` は area/region を画面 pixel と capture 座標に変換します。
非表示・切断・capture 外の矩形には normalized box を与えません。focused editor、
popup の所有権、検証済み gesture surface は確定しません。keymap の上限超過時は
binding を捨てずに snapshot 全体を拒否します。
Linux の入力座標は複数 monitor を含む X11 root ではなく capture した monitor の
寸法を使います。capture/input の範囲が不一致なら Blender 状態の関連付けを拒否します。

新しい observe 応答は `compiled_state`、`state_provider_status`、
`state_pixel_association` を返す場合があります。状態は独自の observation ID を持ち、
capture の近くで parse 前に採取され、parse 中に期限切れになることがあります。
`FOREGROUND_WINDOW_ONLY` は pixel と同時に観測した scene の証拠ではありません。
discovery は schema と既定の実行可否を示し、live `READY` は主張しません。
既存の `API_ASSISTED` fixture 検証はこの新しい production 経路の検証ではなく、
production operation の完全な対応は未完了です。不明な入力文脈を仮定で補わないでください。

typed operation セッションの継続には明示的な `operation` が必要です
(`clef-use continue ... --operation '<JSON>'`)。planner の指示だけでは直前の効果を
繰り返しません。元の目標全体の検証には `operation` を指定せず、
`execution_mode="ASSESS"` の新しい `computer_run` 契約を作成します。CLI では
`clef-use run "Verify the complete original goal" --mode ASSESS` を使います。

`INSTALLED`、`DISCOVERED`、`LOADED`、`INVOKED`、`TASK_VERIFIED` を別々に記録
します。ファイルのコピー、ツール一覧、スキル名の応答だけでは次の段階を通過
しません。live trigger 検証は実際のハーネスの新しいセッションで読み取り専用ツールを
使用します。provider 認証の失敗時、ロードと呼び出しは `NOT_RUN` のままです。
`INVOKED` にはツールの成功応答が必要です。転送が完了しても MCP エラーなら
通過しません。negative trigger は失敗した呼び出しの試行も拒否し、リクエストの
拒否によって不要な trigger が隠れることを防ぎます。
明示的なエラーは `INVOKED=FAIL`、結果がない場合や未完了の場合は `NOT_RUN` です。
作業の検証には、隔離した対象への許可済み入力、外部からの新しい状態確認、
入力とプロセスの終了確認が別途必要です。非公開 API 補助作業の成功は、
production での実行可能性や目標全体の完了を証明しません。

`MODIFIED`・`CONFLICT` はユーザーの編集を保存します。既存の guide の競合は統合状態
ディレクトリに比較用コピーを残します。capability 確認中の変更や guide ファイルの
追加・削除は journal 作成前に適用を止め、preview と変更のない計画も所有権を再確認します。
明示的に無効にした項目は有効にしません。更新後は capability
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
明示した入力 context がある modifier gesture も、移動・押下前に IME の待機状態と
text focus の非アクティブ状態が必要です。通常の pointer gesture は別に扱います。
X11 の左・中央・右ボタンとスクロール方向は現在の OS pointer map に従います。
無効な論理ボタンは入力を拒否します。通常の解放・独立 abort・guardian 復旧では、
押下時に確認した物理ボタンを解放します。
X11 の文字入力は ASCII も明示的な clipboard 方式を使います。キーイベントは
変換開始前でも IME に渡る場合があります。転送確認と入力欄の結果確認は別です。
既存 clipboard 形式を保存できない場合は入力前に拒否します。受信前に中止した
場合、既に送られた貼り付け用の文字を転送完了または別のコピーまで維持し、以前の
データを早く復元しません。Windows 操作は native Unicode を使います。
Windows の押下キー検査は拡張 scan code と modifier の左右を区別し、別のキーの
ユーザー入力があれば後続入力を遮断します。同じ virtual key を共有する物理キー
（例: 二つの Enter）の同時押下は、この照会では区別できません。
Windows guardian は解放に成功したキー・Unicode の ACK を削除します。その後の
親プロセス EOF では、別の所有者が再取得した入力を古い ACK で解放しません。

インストール済み Windows 0.1.36 で、左右・中央クリックと範囲内の
Shift+左/中央ドラッグを実際の非テキスト受信ウィンドウで確認しました。
worker が停止中でもキャンセルで Shift と中央ボタンを解放し、所有 worker
プロセス終了後は別の guardian が解放します。この検証は所有受信側だけの
IME を無効化します。自動 IME 検出、Blender の orbit/pan の意味、ハーネス
による GUI 作業の完了を証明するものではありません。

別のインストール済み 0.1.36 component で実際の CLI/HTTP service abort を検証しました。
injector の停止中に Shift/中央ボタンを解放し、再開後も取り消された injector は
追加入力を拒否します。明示的に登録した session と所有する非テキスト受信窓の検証であり、
完全な gesture/Blender operation admission は未検証です。

別のインストール済み Windows 0.1.37 component は、文書化された debug API で worker
の全スレッドを停止します。attach breakpoint が保留され heartbeat が停止した間に、
別の guardian が6秒の lease deadline で Shift/中央ボタンを解放します。worker EOF や
親の解放呼び出しより前に native 解放を観測し、再開後は実際の watchdog による取消と
追加入力の拒否を確認しました。worker/guardian の終了、正確なポインタ/foreground
復元も成功しました。これは部分的な入力復旧の証拠であり、完全な runtime/service
operation admission、Blender の意味、モデル完了や遅延・性能の結果ではありません。

decision 診断には画像を除く実際の UTF-8 テキスト予算のバイト数、object・question
数、SDK が報告した入力トークン数を保持します。`SDK_USAGE` は 1～8192 の整数、
欠落は `UNAVAILABLE`、不正な報告値は `INVALID` とし、後二者の数は null です。
これらは正しい対象の coverage、校正された信頼度、モデル遅延の測定ではありません。
decision 候補は operation と観測 target ID を保持し、同じ名前の control を位置で
区別できるようにします。対象との対応を保つ変更であり、正しい選択の保証や信頼度
guard の緩和ではありません。
parser の object は正確な座標と異なる action・confidence・source の証拠を個別に
保持し、同等な正規化済み記録だけを重複除去します。明示した visual primitive は
構造化候補の予算計算前に適用され、無関係な文字列候補が click・scroll を押し出しません。
文字列入力候補は、同じラベルの入力欄も含め、一致する観測済み入力欄を個別に保持します。
候補が設定された操作予算を超えると、構造化実行はモデル呼び出しと入力の前に再計画を要求します。
最初の入力欄が正しいと仮定せず、対象範囲を絞ってください。
対象の根拠がない場合や実行対象が 40 個を超える場合、座標の根拠を黙って削除せず拒否します。
全機会の事前適格性・policy 証拠がなければ、反応 coverage は null・`NOT_MEASURED`
のままです。高速な成功入力だけでは出荷 gate を通過しません。実際の OS event
時刻と backend ACK は区別します。
現在、測定で合格した 100ms profile や出荷 gate の成功は主張していません。
[実行証拠](../EXECUTION_STATUS.md)と[検証項目](../../ACCEPTANCE.yaml)を参照してください。

Windows のキャプチャは、スレッド限定の物理座標 context 内で native GDI を使い、process 全体の DPI awareness を変更しません。開いている window と control の物理 geometry を保つ必要があり、キャプチャで変われば検証失敗です。この修正は Blender popup・focus・IME・keymap の状態や100ms反応性能を証明しません。

実際の Windows Codex 検証では discovery・load・invoke と GUI task 成功を分けます。前のクリックが正しくても、tool 応答が LOW_CONFIDENCE なら task は失敗です。実際の候補一覧、独立測定した物理 target geometry、widget 結果を保持し、呼び出し成功を task 成功にするために信頼度 guard を下げません。

現在の Windows state provider は native UI Automation の証拠と optional な
Blender provider を組み合わせます。標準ライブラリのみの base Python worker は
準備完了時に実際の PID を証明し、query の timeout は 500ms です。各結果は
query 前後の native foreground 観測を同じ focused UIA element、process identity、
ancestor chain、bounds に結び付けます。対応する TextEdit で
`GetActiveComposition` が null composition とともに `S_OK` を返す場合は `False`
です。未対応 interface、エラー、古い証拠や一致しない証拠は `UNKNOWN` のままです。
focus identity は UIA runtime ID と物理 bounds も結び付けます。編集可否には明示的な
enabled・non-password 属性と、別途登録された TextPattern の document range の
Boolean IsReadOnly が必要です。TextEdit 対応だけでは確定せず、文字内容は読みません。
popup 所有状態、keymap、全体の idle、Blender operation admission は証明しません。
installed 0.1.39 では InputIR の active composition 拒否と危険な legacy type bypass を
別々に再現しました。別の immutable installed 0.1.40 では正確な Unicode、
活動中の composition に対する四経路の拒否、選択・削除、Enter のフォーカス移動、
独立 abort・復旧が通過しました。実際の Codex GUI 作業は既存の mode-confidence
基準で失敗し、browser model 作業は parser timeout で失敗しました。入力の到達、
作業成功、100ms 性能基準を区別します。
[installed 証拠](../validation/2026-10-13/windows-installed-ci-0140.json)を参照してください。

Hermes は MCP 起動時に親環境変数を除去します。検証では選択した管理サーバーの
native メモリ登録に読み取り専用設定を適用し、ディスク設定、認証、モデル選択、
native CLI prompt を保持します。モデル実行前に実際の capability/status 二ツールの
schema 一致を確認します。同時応答には全文または限定 preview の一意な一致が必要です。
共通 prefix は曖昧なまま扱い、副作用を伴うツールの試行は検証失敗になります。
この制限は MCP の範囲です。native `skills` toolset は `skill_manage` も公開するため、
プロセス全体の書き込み禁止を証明しません。この試行は検証失敗となり、観測した
呼び出しと権限を区別して記録します。

OMP は native 遅延登録で初期ツール一覧に writer を追加できます。検証は一時的な
native approval overlay で writer と既存の非照会権限を拒否し、reader の deny/prompt
と引数別の読み取り承認等級を保持します。native SDK 全文をサイズ制限付き非公開
ファイルから読み、guide 全文と runtime/schema 契約を確認します。先の失敗や未知の
呼び出しは後の成功や期限切れで消しません。管理 integration lock で直列化し、
native helper 失敗後はモデルを開始しません。ディスク設定を保持し overlay を除去します。
[実際の Windows .41 インストール](../validation/2026-10-13/windows-installed-ci-0141.json)は
CI15/15・更新・再実行を通過しました。作業失敗と数値基準は別の証拠です。

Hermes live 検証は native event stream を保持し、installed harness の読み取り専用
session export API で同じセッションだけを読みます。guide 全文と runtime 応答は
元の stream バイト、session/call ID、管理 contract と一致する必要があります。
spillover は選択した profile と call に限定します。切れた preview、エラー、曖昧な
call は成功の証拠ではありません。完全な export が利用できなければ `NOT_RUN` です。
後の呼び出しが成功しても先の失敗を保持し、native catalog と model trigger の段階を
区別します。

Windows の model keyboard action は State Compiler と InputIR を経由します。文字の
target は既に focus された編集可能な control と一致する必要があり、type は暗黙の
focus click を行いません。IME・identity・編集可否が UNKNOWN なら拒否します。
native 単位ごとに fresh guard で focus と composition を確認します。keyboard と
modifier input は observed context と live guard が必要です。明示的な Escape と
owned recovery release は独立して維持し、context 不在を idle IME と見なしません。
一度の Enter の伝達 ACK 後は focus が移動できます。後続確認は元の native
window/process/thread に結び付け、release と伝達記録のみを許可します。伝達済みでも
未検証の入力は実行予算を消費し、NEEDS_REPLAN となります。伝達だけで完了しません。

Windows native input は入力前に failsafe を確認し、PyAutoGUI を import しなく
なりました。installed 0.1.38 の probe は入力を送る前に、所有 window の geometry
を `[210,210,1638,1066]` から `[120,120,936,609]` に変化させました。input count は
0 でした。同じ経路への source 修正では geometry が維持されました。これは source
の証拠であり、installed 0.1.38 の PASS ではありません。100ms 性能の主張には
つながりません。

watchdog スレッドでも window bounds は物理座標で取得します。Windows 検証では
widget の入力点を物理 bounds に変換し、native 受信 window の所有権を確認します。
capture の成功だけでは入力座標の正しさを証明しません。
button-down と wheel は、native pointer 受信側の root window が観測済み foreground
window と一致する場合だけ送信します。foreground の一致だけでは別 window への入力を
許可しません。所有入力の recovery release はこの条件に依存しません。
