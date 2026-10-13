# 代理安装、使用与恢复

runtime wheel 包含三个仅提供指导的通用技能：`clef-use`、`clef-use-blender`、
`clef-use-diagnostics`。默认选择 core 和 diagnostics；Blender 需要明确选择。
应用前预览具体路径，只更改选定目标。首次无人值守安装不会在没有
`--integrate codex|hermes|omp|all` 时注册新工具环境。模型准备是独立选项。

编辑和只读菜单、状态评估都应加载 Blender 技能。`references/` 文件属于原技能。
在 Hermes 中使用
`skill_view(name="clef-use", file_path="references/API_BASELINE.md")` 读取基准 API。

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
TextEdit 是否只读或可编辑尚未观测。该 provider 不证明 popup 所有权、keymap 状态、
全局 idle 或 Blender operation admission。新 provider 的 installed end-to-end 验证仍待
完成；这不代表 live readiness 或 operation 成功。

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
