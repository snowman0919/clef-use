# 代理安装、使用与恢复

不可变 .50 CI 已通过 15 个平台的安装与归档检查。专用 Windows 候选安装使用
`--integration-preview`，通过 CLI 安装、CURRENT、文件和 LIMITED 令牌下的 MCP 检查。
另一会话正在操作 Windows，因此保留共享 .49 和活动工具环境注册。标准更新、
原生 Codex .50 与 GUI E2E 仍为 NOT_RUN。
参见[候选验证记录](../validation/2026-10-14/windows-isolated-ci-0150.json)。

OMP 也能用 `write xd://<tool>` 传输只读 MCP 调用。验证只认可原生目标、参数、服务器、
结果和实际消费者载荷完全匹配的调用；不能仅凭方法名称判断文件写入或安全读取。
加载指南前的调用、实际被拒绝的写入以及不匹配仍判定失败。
参见[源代码 .50 记录](../validation/2026-10-14/omp-device-evidence-0150.json)，原生组件、
保留 trace 的重新判定与新的模型执行分别记录。

不可变的 .49 CI 已通过 15 个平台的安装检查及归档与源文件对照。
实际 Windows .48 -> .49 更新、重复 CURRENT、LIMITED 令牌下的软件包与 MCP 检查，
以及原始 Codex explicit/natural/negative 模型案例也已通过。这些无窗口检查不能证明
GUI 任务成功或 100ms 输入延迟。此前 Hermes/OMP 失败仍保留，公开部署守卫不变。
参见[安装验证记录](../validation/2026-10-14/windows-installed-ci-0149.json)。

runtime wheel 包含三个仅提供指导的通用技能：`clef-use`、`clef-use-blender`、
`clef-use-diagnostics`。默认选择 core 和 diagnostics；Blender 需要明确选择。
应用前预览具体路径，只更改选定目标。首次无人值守安装不会在没有
`--integrate codex|hermes|omp|all` 时注册新工具环境。模型准备是独立选项。

只读验证从 Hermes 的原生工具定义 factory 中移除 `skill_manage`，覆盖 MCP 更新和
延迟发现列表，并拒绝其 registry 执行。原生 Skill reader 及原始 schema 保持可用。
reader 使用 metadata 仍可能变化，因此指南和配置文件字节未变不代表全部原生生成
状态未变。OMP 验证通过临时启动策略等待实时 MCP 发现完成，保存的设置和声明的
模型时限保持不变。

实际 .48 专用 Linux 桌面的缓存验证与 Windows 安装验证分别记录。
Hermes 在仅对本次执行生效的私有只读限制下，不把缓存当作完成证据，并确认了新的
Continue 画面。OMP 的当前活动会话默认值缓存子项通过，但在加载指南之前调用
status，因此整个原生案例仍为 FAIL。读取真实 status/cache 后，显式 ID 验证仍失败。
OMP 在启动等待期间可能公布缓存工具列表；临时 `mcp.startupTimeoutMs: 0` 等待实时
发现完成，不更改保存的设置。这些只读案例不能证明 GUI 输入准确度或 100ms 延迟。
参见[验证记录](../validation/2026-10-14/linux-native-cache-0148.json)。

工具环境的 JSON 流按 UTF-8 解码，不依赖 Windows locale。
runtime 调用失败后，即使后续 capability 调用成功，验证仍保持 FAIL。
仅发现技能不能证明模型已加载指南或调用工具。
文件读取和已公布的 guide resource 必须匹配完整受管理正文。
capability 的 runtime/schema/guide hash 和只读双工具 facade 也必须匹配。
在调用之后才加载所需指南时，验证顺序为 FAIL。
先开始的 runtime 调用仍为 FAIL，后续加载、成功或进程异常退出不会抹去该证据。
原生 Skill catalog 发现与 runtime 调用分开判断。
operation 详细响应必须与先前已验证的实时列表中的对应 operation 完全一致。
仅有 status 响应不能验证当前 capability 列表。

Codex 命令启动失败可能没有 JSON command event，只记录在私有 stderr 中。
原生 runner pipe 连接超时始终保留为 `NATIVE_EXECUTOR_STARTUP_TIMEOUT` FAIL，
不受后续成功或异常退出影响。报告只公开阶段、超时时间、指南读取尝试标志和
证据 hash。读取尝试不能证明正文已加载；此错误本身也不能确定认证问题或
原生执行器失败的具体原因。

MCP 连接指引仅适用于已授权的 GUI 工作或明确的 clef-use capability/schema
请求。普通代码问题及禁止 runtime 访问的请求不应选择这些工具。只读连接说明
实际公布的 capability/status 工具和 schema/guide resource。发现 capability
不需要正在运行的 GUI service；status 读取已有的 service/session，不能用于
发现 Blender 的隐藏状态。
在 OMP 中，通过所属技能的原生 reader 读取链接文件，例如
`read(path="skill://clef-use/references/API_BASELINE.md")`。保留此 URI，不要转成
`file://`。先发现实际 resource reader 再访问 MCP resource，不要猜测服务器别名或
resource 地址。

OmniParser 在 upstream import 前后保留调用者的 Torch thread 数，
包括显式的单 thread 设置，无需新增 thread 配置。
此初始化修复本身不能证明任务完成或 100ms 输入延迟；
请使用实际安装的 runtime 分别验证。

编辑和只读菜单、状态评估都应加载 Blender 技能。`references/` 文件属于原技能。
在 Hermes 中使用
`skill_view(name="clef-use", file_path="references/API_BASELINE.md")` 读取基准 API。
只读 GUI capability/schema 问题也适用这些指南。先发现 Skill catalog，加载 core
及适用的 Blender 指南，再调用 runtime 工具；不发送输入的 capability 请求也是调用。

OMP 将 `PI_CONFIG_DIR` 解析为相对于 HOME 的路径名称，默认是 `.omp`。
绝对路径的默认 agent 目录请使用 `PI_CODING_AGENT_DIR`。
明确为空或 `default` 的 `OMP_PROFILE` 优先于 `PI_PROFILE`，选择默认配置。

如果注册的可执行文件指向固定的旧安装，`refresh` 会保留该路径并拒绝不兼容的新指南。
`--command-path` 也不会覆盖现有注册。先用 `--dry-run` 检查受管理项的删除，
仅删除未修改的受管理项，再通过 `--command-path` 注册当前可执行文件。
用户修改及已禁用条目的冲突会被保留。

<!-- clef-use:commands -->
operation 的 `SUCCEEDED` 只验证类型化效果。自然语言目标需要另一次 fresh
`ASSESS`，因此会话返回 `NEEDS_REPLAN`。验证时使用
`--trigger natural|explicit|negative|native` 区分模型触发与 native adapter 验证。

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

发现当前 schema 后提交可验证的小目标。指定精确文本，并区分字符输入与快捷键；
不要猜测 keymap。`ASSESS` 不发送输入。缓存观察不能授权新的 pointer，也不能
证明最终完成。本地 operation 是有类型的有限状态过程，与 Agent Skill 的自然
语言指导分离。可信本地观察器必须验证 editor、selection、mode、IME 和 keymap。
有可信状态依据时，guard 会比较 keymap 内容和版本名。
viewport 手势执行前及过程中会重新检查 editor 区域；区域变化时停止执行并释放自有输入。
view 基线也必须保持到 native 手势按钮输入被确认。此前的独立 view 变化不能算作
手势成功；确认后的 drag 变化在保留其他 guard 的前提下允许。
数值 transform 需要位移、旋转及 scale 的完整 XYZ readback。输入前重新检查
transform 上下文，进入前检查初始值，commit 前检查已验证的 preview；不能仅凭部分
成分判断其他轴未变。property 编辑后比较所有已观察字段和 object ID，但不能据此
确认未观察字段保持不变。
数值 literal 保留请求的 float；应用实际 readback 仍须满足请求的 tolerance。
改变状态的 operation 和自有 modal 取消需要完整、稳定的 `selection_identities`。
Blender 使用进程范围的公开 `session_uid`；改名保留 ID，同名对象被替换时阻止
后续输入。缺失 ID 时保持 UNKNOWN。observer 还提供位置和 scale 的 X/Y/Z 属性。
使用前请发现 operation registry v6。
数值移动要求完整、新鲜的 `scene_units`，并在输入、readback 和所拥有 modal 的取消期间
保持相同 scene 转换。单位名称不变也不能排除 scene 比例变化。amount/readback 保持
已验证的 operation 单位，NONE 保持原始值。转换缺失或改变时阻止后续输入和成功判定。
旋转和 scale 不要求 scene 长度设置。
角度 readback 必须符合 DEGREES/RADIANS 声明，exact-property 坐标保持原始值。
位置 `property_edit.value` 表示 Blender 单位的原始坐标。新鲜的 `scene_units`
证据决定显式米制输入，并在输入与 readback 期间保持固定。单位缺失或变化会阻止
输入或成功判定。scale 为无量纲；显示单位不会重新解释请求的原始坐标，实际
readback 仍须满足原 tolerance。
未知状态会阻止输入。默认截图观察器不能确认 Blender 的隐藏状态。API 辅助
fixture 的通过不能证明 pixels-only 操作成功。
截图产生的坐标和 foreground 保留捕获时刻；捕获或处理延迟不会更新有效期。
provider 独立观察的值按各自的时刻判断。
Windows 字符输入在发送前验证 UTF-16，并在每个 native 单位前重新检查当前 guard。
状态观察后也会重新检查取消与 deadline。X11 确认在 paste 尝试前取消时，先释放
自有 modifier，再经 native ACK 恢复支持的原 clipboard 格式；保留用户的并发复制。
如果 paste 可能已送达，则保留待粘贴文本；没有恢复 ACK 时报告未解决状态。
legacy X11 键盘输入也会在按键前验证当前绑定，包括隐式 Shift。缓存绑定发生变化时
拒绝输入；释放使用已确认的物理 keycode，不释放外部已按住的键。
Blender view 效果使用单一、完整且无歧义 viewport 的实际 view matrix 和 perspective
mode。仅 region、layout 或 projection 变化不能证明 orbit/pan；pose 缺失或 quad
view 有歧义时保持 UNKNOWN。

默认 provider 仍为 `NONE`；截图和 native window identity 不能确认 Blender 的隐藏状态。
Linux X11 和 Windows 支持可选的只读 Blender observer。`clef-use blender-observer-script` 会输出
已安装脚本的路径，请将该确切路径传给已获准使用的 Blender 可执行文件。在 private
父目录下指定一个尚不存在的新目录，脚本会创建 private 目录和 endpoint；它不会自动
连接到已运行的 Blender。

```sh
clef-use blender-observer-script
blender --python "/absolute/installed/blender_observer.py" -- --clef-state-dir "/absolute/private/new-observer"
```

在 runtime 的 `config.toml` 顶层设置以下选项。默认文件为
`~/.config/clef-use/config.toml`，也可通过 `CLEF_USE_CONFIG` 选择其他文件。

```toml
blender_state_socket = '/absolute/private/new-observer/state.sock'
```

listener 从 Blender 的首个 UI timer 启动。Linux 验证 Unix `SO_PEERCRED` 和 XRes
kernel process identity。Windows 使用显式 `127.0.0.1` listener；`state.sock` 是
private NTFS port metadata，而非 Unix socket。native TCP peer PID 与 process token
user 必须匹配 foreground process。两平台均要求唯一 RNA window/client 的物理 pixel
尺寸匹配，且 native foreground 未改变。UI timer 被阻塞时 provider 为 unavailable，
不能判定 idle。observer 读取 window、selection、object mode、原始 transform/unit、
viewport 和已观察到的 modal operator，不修改 scene 或执行 operator。popup、text focus、
IME、有效 keymap 和整体 idle 状态仍然未知。空 operator 列表也不能证明不存在。
即使配置了此部分 observer，只要缺少必要的已验证状态，六个 operation 仍返回 `BLOCKED`。

observer 在可用时保留所属 manager 的公开 `interface_locked` Boolean。只有通过 native
identity、window 和新鲜度验证的 `true` 才形成 busy 阳性证据 `loading=true`。
`false` 或不可用时，`loading` 保持 UNKNOWN。解除锁定后仍可能存在 modal 或其他输入
所有者，因此不能用此值授权输入或判定 idle。

`active_tool` 表示独立绑定的 native context mode 下配置的 VIEW_3D workspace tool，
并保留 workspace 和已观察到的 area ID。缺失或歧义时保持 UNKNOWN。
focused editor 和有效 dispatch 也保持 UNKNOWN，不能仅凭此值授权输入。
collector 只读取已初始化的引用，不创建或刷新 tool，超过 128 个时拒绝读取。

`keymap_inventory` 保留合并 user keymap 中的相关 binding、重复和禁用项、
tri-state modifier（`-1` 表示 any）及内容 digest。它是原始列表，不是代表实际
dispatch 的 `keymap` 或 `keymap_version`。`editor_layout` 将 area/region 转为屏幕
pixel 和 capture 坐标；隐藏、裁切或 capture 外的矩形没有 normalized box。
它不确定 focused editor、popup 所有权或已验证的 gesture surface。超过 keymap
上限时拒绝整个 snapshot，不丢弃 binding。
Linux 输入坐标使用捕获 monitor 的尺寸，不使用跨多个 monitor 的 X11 root 尺寸。
capture/input 范围不一致时拒绝关联 Blender 状态。

新的 observe 响应可包含 `compiled_state`、`state_provider_status` 和
`state_pixel_association`。状态有独立的 observation ID，在 capture 附近、parse 之前
采样，可能在 parse 期间过期。`FOREGROUND_WINDOW_ONLY` 关联不是与 pixel 同步的
scene 证据。discovery 描述 schema 和默认可用性，不宣称 live `READY`。既有
`API_ASSISTED` fixture 验证不能证明此新 production 路径通过验证；完整的 production
operation 支持仍未完成。不要用假设补全未知的输入上下文。

继续 typed operation 会话必须明确提供 `operation`
(`clef-use continue ... --operation '<JSON>'`)；仅提供 planner 指导不会重复上次效果。
要验证原始目标的全部内容，请新建 `computer_run` 契约，设置
`execution_mode="ASSESS"` 并省略 `operation`。CLI 可使用
`clef-use run "Verify the complete original goal" --mode ASSESS`。

分别记录 `INSTALLED`、`DISCOVERED`、`LOADED`、`INVOKED`、`TASK_VERIFIED`。
文件复制、工具列表或技能名称回显不能证明后续阶段。live trigger 验证使用实际工具环境
的新会话，只开放只读工具。provider 身份验证失败时，加载和调用保持 `NOT_RUN`。
`INVOKED` 要求工具成功响应；传输完成但返回 MCP 错误不能通过。negative trigger
也拒绝失败的工具调用尝试，避免用请求被拒绝掩盖不必要的 trigger。
明确错误记为 `INVOKED=FAIL`；缺少结果或尚未完成时保持 `NOT_RUN`。
任务验证还需要在隔离目标中执行已获授权的输入，重新检查外部状态，并确认输入和
进程已清理。私有 API 辅助任务通过不能证明 production 可用性或整个目标完成。

`MODIFIED` 或 `CONFLICT` 保留用户修改。已有 guide 冲突会在集成状态目录留下比较副本。
capability 查询期间的修改或 guide 文件新增、删除会在 journal 创建前停止应用；
preview 和无变更计划也会重新检查所有权。
明确禁用的条目不会重新启用。更新后检查 capability 版本，并重新加载缓存客户端。
卸载只删除未修改的受管条目。Hermes 不支持 project scope，请使用选定的 user
profile。移动技能前检查 source 和 shadow 状态。

本地请求绑定执行文件版本、runtime protocol 和 API 指纹。旧客户端不能停止或控制
新服务；发生不匹配时，请重新加载当前执行文件和 MCP 会话。新客户端可以替换空闲
的旧服务，但正在执行输入或等待 modal 恢复时会拒绝替换。更新前已运行的会话，
请先用保留的同版本执行文件完成或中止。不可修改的旧客户端可能隐藏服务器的重新
加载说明，只显示一般拒绝信息。同版本的 protocol 或 schema 不匹配时，必须明确
停止空闲服务后再重新加载，不会自动重启。

仅中止自己的会话并验证输入释放。精确 Unicode clipboard 插入与 IME 组合不同；
IME 活动或未知时会阻止快捷键。watchdog 恢复受 OS 权限和确认时间窗口限制。
有明确输入 context 时，modifier gesture 也必须在移动或按下前确认 IME 空闲且
text focus 未激活。普通 pointer gesture 单独处理。
X11 的左、中、右按钮及滚动方向遵循当前 OS pointer map。禁用的逻辑按钮会拒绝
输入。正常释放、独立 abort 和 guardian 恢复均释放按下时确认的物理按钮。
X11 的字符输入（包括 ASCII）要求显式 clipboard 方式；键事件即使在组合开始前
也可能进入 IME。传输确认不等于输入框结果验证。无法保留原有 clipboard 格式时，
会在输入前拒绝。接收前中止时，为已发送的粘贴保留文字，直到传输完成或发生其他
复制，不提前恢复旧数据。Windows 操作使用 native Unicode 输入。
Windows 按键检查保留扩展 scan code 和 modifier 左右区别；检测到用户按住其他
键时会阻止后续输入。共享同一 virtual key 的物理键（例如两个 Enter）的同时按下
无法通过此查询区分。
Windows guardian 会移除已成功释放的键与 Unicode ACK；之后父进程 EOF 不会用
旧 ACK 再次释放已被其他所有者重新按下的输入。

已安装的 Windows 0.1.36 通过实际非文本接收窗口验证了左/右/中键点击和
限定区域内的 Shift+左/中键拖动。worker 阻塞时，取消仍会释放 Shift 和中键；
自有 worker 进程终止后，独立 guardian 也会释放它们。此验证仅禁用自有接收
窗口的 IME，不能证明自动 IME 发现、Blender orbit/pan 语义或 harness GUI
任务完成。

另一个安装版 0.1.36 component 验证了实际 CLI/HTTP service abort：injector 被阻塞时
释放 Shift/中键，解除阻塞后已取消的 injector 仍拒绝追加输入。它使用显式注册的
session 和自有非文本接收窗口。完整 gesture/Blender operation admission 尚未验证。

另一个安装版 Windows 0.1.37 component 使用文档化的 debug API 暂停 worker 的所有线程。
attach breakpoint 保持待处理且 heartbeat 不变时，独立 guardian 在6秒 lease deadline
释放 Shift/中键。native 释放发生在 worker EOF 或父进程释放调用之前；恢复后还确认
实际 watchdog 取消及追加输入拒绝。worker/guardian 退出、精确指针及 foreground 恢复
均通过。这只是部分输入恢复证据，不代表完整 runtime/service operation admission、
Blender 语义、模型任务完成或延迟/性能结果。

decision 诊断保留不含图像的实际 UTF-8 文本预算字节数、object/question 数量和
SDK 报告的输入 token 数。`SDK_USAGE` 表示 1～8192 的整数；缺失时为
`UNAVAILABLE`，报告值无效时为 `INVALID`，后二者的数量均为 null。
这些计数不衡量正确目标的 coverage、校准置信度或模型延迟。
decision 候选保留 operation 和观测 target ID，使同名控件可按位置区分。这只保留
候选与目标的对应关系，不保证选择正确，也不放宽置信度 guard。
parser 对象分别保留精确坐标及不同的 action、confidence、source 证据，只对等价的
规范化记录去重。明确的 visual primitive 会在结构化候选预算前应用，避免无关文字
选项挤掉请求的 click 或 scroll。
字符串输入候选会分别保留所有匹配的已观测输入框，包括同名输入框。
这些选项超过配置的动作预算时，结构化执行会在调用模型或输入前请求重新规划。
请缩小目标范围，不要假定第一个输入框就是正确目标。
缺少目标依据或不同执行目标超过 40 个时会拒绝，不会静默删除决策上下文中的坐标依据。
缺少所有机会的事前资格及 policy 证据时，反应 coverage 保持 null/`NOT_MEASURED`。
仅有快速成功的输入不能通过发布 gate；实际 OS event 时刻与 backend ACK 分开记录。
目前不宣称已测得通过的 100ms profile 或发布 gate 成功。
参阅[执行证据](../EXECUTION_STATUS.md)及[验收要求](../../ACCEPTANCE.yaml)。

Windows 截图在仅限当前线程的物理坐标 context 内使用 native GDI，不修改整个 process 的 DPI awareness。必须保留已打开 window 与 control 的物理 geometry；截图使它们发生变化即验证失败。此修正不证明 Blender popup、focus、IME、keymap 状态或100ms反应性能。

实际 Windows Codex 验证区分 discovery、load、invoke 与 GUI task 成功。即使前一次点击正确，tool 返回 LOW_CONFIDENCE 仍是 task 失败。保留真实候选列表、独立测量的物理 target geometry 和 widget 结果，不降低置信度 guard 来把调用成功变成 task 成功。

当前 Windows 状态 provider 将 native UI Automation 证据与可选的 Blender
provider 组合。仅依赖标准库的 base Python worker 在就绪时验证其实际 PID，query
超时为 500ms。每次结果都把 query 前后的 native foreground 观测绑定到同一个
focused UIA element、process identity、ancestor chain 和 bounds。对于受支持的
TextEdit，`GetActiveComposition` 返回 `S_OK` 且 composition 为 null 时表示
`False`；interface 不受支持、发生错误、证据过期或不匹配时均保持 `UNKNOWN`。
focus identity 还绑定 UIA runtime ID 与物理 bounds。可编辑状态必须有明确的 enabled、
non-password 属性，以及单独注册的 TextPattern document range 返回的 Boolean
IsReadOnly。仅支持 TextEdit 不足以证明，且不读取文本内容。这不证明 popup 所有权、
keymap、全局 idle 或 Blender operation admission。installed 0.1.39 已分别验证 InputIR
拒绝活动组合以及危险的 legacy type bypass。另行验证的 immutable 安装版 0.1.40
通过了准确 Unicode、活动组合时四条路径的拒绝、选择和删除、Enter 焦点转移及独立
abort 和恢复。实际 Codex GUI 任务仍未通过原有 mode-confidence 门槛，browser model
任务因 parser timeout 失败。输入到达、任务成功和 100ms 性能门槛必须分别记录。
参见[安装版证据](../validation/2026-10-13/windows-installed-ci-0140.json)。

Hermes 在启动 MCP 时过滤父环境变量。验证在选定受管服务器的 native 内存注册中
设置只读权限，保留磁盘配置、认证、模型选择及 native CLI prompt。模型执行前必须
确认实际 capability/status 两个工具的 schema。并发响应必须与完整响应或有限 preview
唯一匹配；相同 prefix 仍视为歧义。任何有副作用的工具尝试都会导致验证失败。
此限制仅适用于 MCP。native `skills` toolset 仍包含 `skill_manage`，因此不能证明
整个进程禁止写入。此工具尝试会使验证失败；证据必须区分观测到的调用与实际权限。

OMP 的 native 延迟注册可将 writer 重新加入初始工具列表。验证使用临时 native
approval overlay 拒绝 writer 及既有非查询授权，保留 reader 的 deny/prompt 和参数
相关读取审批等级。完整 native SDK 结果通过限长私有文件读取，并核对 guide 全文、
runtime/schema 契约。先前失败和意外工具尝试不会被后续成功或超时抹去。验证与受管
integration 共用锁；native helper 失败后不启动模型。磁盘设置保留，overlay 随后删除。
[实际 Windows .41 安装](../validation/2026-10-13/windows-installed-ci-0141.json)通过
CI15/15、更新和重复执行；原有任务失败与数值验收门槛仍单独记录。

Hermes live 验证保留 native event stream，并通过安装版 harness 的只读 session
export API 仅读取对应会话。完整 guide 正文和 runtime 响应必须与原始 stream 字节、
session/call ID 和管理 contract 一致；spillover 仅限选定 profile 和 call。截断
preview、错误或不明确的 call 不能证明调用成功；无法获取完整 export 时为 `NOT_RUN`。
后续调用成功也保留前面的失败，并区分 native catalog load 与 model trigger 阶段。

Windows model keyboard action 经过 State Compiler 与 InputIR。文字 target 必须已是
获得 focus 且可编辑的 control，type 不再隐式点击输入框。IME、identity 或可编辑状态
未知时拒绝输入，并在每个 native 单位前用 fresh guard 检查 focus 与 composition。
keyboard、modifier input 必须有 observed context 和 live guard。明确的 Escape 与
owned recovery release 保持独立；context 缺失不代表 IME idle。
单次 Enter 获得传递 ACK 后允许 focus 移动；后续检查仍绑定原 native
window/process/thread，仅允许 release 与传递记录。已传递但未验证的输入也消耗执行
预算，并返回 NEEDS_REPLAN；传递本身不证明目标完成。

Windows native input 会在发送前检查 failsafe，且不再 import PyAutoGUI。installed
0.1.38 的一次 probe 在未发送任何 input 时，将自有 window geometry 从
`[210,210,1638,1066]` 改为 `[120,120,936,609]`，input count 为 0。同一路径的
source 修正保留了 geometry。这是 source 级证据，不是 installed 0.1.38 PASS，
也不支持任何 100ms 性能声明。

watchdog 线程同样使用物理 window bounds。Windows 验证会把 widget 输入点映射到
物理 bounds，并检查 native 接收 window 的所有权；capture 成功本身不能证明输入
坐标正确。
发送 button-down 或 wheel 前，native pointer 接收方的 root window 必须与绑定的
foreground window 一致。仅 foreground 匹配不能授权向其他 window 输入；已持有
输入的 recovery release 不依赖这一条件。
