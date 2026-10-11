# 代理安装、使用与恢复

runtime wheel 包含三个仅提供指导的通用技能：`clef-use`、`clef-use-blender`、
`clef-use-diagnostics`。默认选择 core 和 diagnostics；Blender 需要明确选择。
应用前预览具体路径，只更改选定目标。首次无人值守安装不会在没有
`--integrate codex|hermes|omp|all` 时注册新工具环境。模型准备是独立选项。

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
文件复制、工具列表或技能名称回显不能证明后续阶段。live 验证使用实际工具环境
的新会话，只开放只读工具。provider 身份验证失败时，加载和调用保持 `NOT_RUN`。

`MODIFIED` 或 `CONFLICT` 保留用户修改，并在集成状态目录留下比较副本。
明确禁用的条目不会重新启用。更新后检查 capability 版本，并重新加载缓存客户端。
卸载只删除未修改的受管条目。Hermes 不支持 project scope，请使用选定的 user
profile。移动技能前检查 source 和 shadow 状态。

仅中止自己的会话并验证输入释放。精确 Unicode clipboard 插入与 IME 组合不同；
IME 活动或未知时会阻止快捷键。watchdog 恢复受 OS 权限和确认时间窗口限制。
目前不宣称已测得通过的 100ms profile 或发布 gate 成功。
参阅[执行证据](../EXECUTION_STATUS.md)及[验收要求](../../ACCEPTANCE.yaml)。
