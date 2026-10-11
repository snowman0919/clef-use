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
未知状态会阻止输入。默认截图观察器不能确认 Blender 的隐藏状态。API 辅助
fixture 的通过不能证明 pixels-only 操作成功。

默认安装只使用截图和可获得的 native window identity，不包含可信的 Blender
application provider，也没有公开的 provider 配置路径。由于缺少经过验证的状态，
六个已注册 operation 都会返回 `BLOCKED`。discovery 分别报告已实现的 schema 和
默认环境的可用性，不宣称实际处于 `READY` 状态。只有受控 `API_ASSISTED` Blender
fixture 中的过程得到验证。通用 production provider 仍是未完成的要求；不要用
假设代替未知的 focus、IME 或 popup 状态。

继续 typed operation 会话必须明确提供 `operation`
(`clef-use continue ... --operation '<JSON>'`)；仅提供 planner 指导不会重复上次效果。
要验证原始目标的全部内容，请新建 `computer_run` 契约，设置
`execution_mode="ASSESS"` 并省略 `operation`。CLI 可使用
`clef-use run "Verify the complete original goal" --mode ASSESS`。

分别记录 `INSTALLED`、`DISCOVERED`、`LOADED`、`INVOKED`、`TASK_VERIFIED`。
文件复制、工具列表或技能名称回显不能证明后续阶段。live trigger 验证使用实际工具环境
的新会话，只开放只读工具。provider 身份验证失败时，加载和调用保持 `NOT_RUN`。
任务验证还需要在隔离目标中执行已获授权的输入，重新检查外部状态，并确认输入和
进程已清理。私有 API 辅助任务通过不能证明 production 可用性或整个目标完成。

`MODIFIED` 或 `CONFLICT` 保留用户修改，并在集成状态目录留下比较副本。
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
X11 的字符输入（包括 ASCII）要求显式 clipboard 方式；键事件即使在组合开始前
也可能进入 IME。传输确认不等于输入框结果验证。无法保留原有 clipboard 格式时，
会在输入前拒绝。接收前中止时，为已发送的粘贴保留文字，直到传输完成或发生其他
复制，不提前恢复旧数据。Windows 操作使用 native Unicode 输入。
decision 诊断保留不含图像的实际 UTF-8 文本预算字节数、object/question 数量和
SDK 报告的输入 token 数。`SDK_USAGE` 表示 1～8192 的整数；缺失时为
`UNAVAILABLE`，报告值无效时为 `INVALID`，后二者的数量均为 null。
这些计数不衡量正确目标的 coverage、校准置信度或模型延迟。
目前不宣称已测得通过的 100ms profile 或发布 gate 成功。
参阅[执行证据](../EXECUTION_STATUS.md)及[验收要求](../../ACCEPTANCE.yaml)。
