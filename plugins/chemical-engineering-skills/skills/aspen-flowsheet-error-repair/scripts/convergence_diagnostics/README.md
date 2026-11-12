> Main-library relocation: plugins/chemical-engineering-skills/skills/aspen-flowsheet-error-repair/scripts/convergence_diagnostics. Source and transformations: [RELOCATION.json](RELOCATION.json). Historical source/admission statements below retain their original scope; current parent skill owns routing and acceptance.

# 收敛诊断离线工具

三项标准库工具，对应[二分定位、精度核查与冷启动方法](METHOD_REFERENCE.md)。
代码MIT；方法说明CC BY 4.0。状态：公开method/code reference，非工程executed_success。

| 工具 | 输入与产物 | 边界 |
|---|---|---|
| `make_isolation_variants.py` | 受保护文本源、显式编辑计划→同源隔离变体与SHA清单 | 不自动选择切断点、删控制或判断因果；各分支有效性由专业owner复核 |
| `audit_precision_trials.py` | 明确目标/单位/容差及内层准则、试验观测→残差和可比精度核查 | 不跨量定义比较容差，不给精度默认值，不自动判根因 |
| `audit_cold_starts.py` | 观测值、操纵量初终值/阈值、启动类型及证据文件→目标/位移/哈希/覆盖核查 | 初始化类型为调用者声明；不自行解释原生报告，不授予strict通过 |

## 使用顺序

先在当前项目中冻结物理/控制/初值与所有单位，再按方法说明设计有效的隔离对照。编辑计划的每个匹配次数必须明确；原源保持不变，变体写入新的目录。包含多字节原生输入时显式选择已确认的编码；脚本不能代替原生导入验证。

```text
python -B -X utf8 plugins/chemical-engineering-skills/skills/aspen-flowsheet-error-repair/scripts/convergence_diagnostics/make_isolation_variants.py --help
python -B -X utf8 plugins/chemical-engineering-skills/skills/aspen-flowsheet-error-repair/scripts/convergence_diagnostics/audit_precision_trials.py --help
python -B -X utf8 plugins/chemical-engineering-skills/skills/aspen-flowsheet-error-repair/scripts/convergence_diagnostics/audit_cold_starts.py --help
python -B -X utf8 -m unittest discover -s plugins/chemical-engineering-skills/skills/aspen-flowsheet-error-repair/scripts/convergence_diagnostics/tests -v
```

`examples/`为合成输入格式示例，字段以各工具`--help`与示例为准。示例不含实际模型参数，也不代表可导入Aspen的工艺输入；启动示例的证据文件应由调用者提供，实际SHA不可用占位文本冒充。

所有目标、绝对容差、内层容差、变量/准则/单位和位移判据均显式传入。**没有推荐精度；1e-6不作通用默认值。**单位不一致保持错误或不可比，不默默换算；未知值不补零。

隔离变体、观测清单和证据哈希存于使用者自己的项目中。产物可能包含其模型片段或路径，应按该项目权限管理；不要把实际使用产物提交本公共目录。

## 实际运行与证据接口

本包只准备文本变体和核查已给定的离线数据。调用者应通过现有Aspen操作owner运行每个受控变体，取得当前版本的真实输入/结果导出、Control Panel、完整history、关闭与资源释放证据。可以将原生审核回执作为artifact绑定；文件哈希与观测清单本身不证明原生通过或数值确实由文件提取。

复用已存在的[运行监督器](https://github.com/milklong888/chemical-engineering-skills/blob/98a2ea53a127cad7e2fecd0df447a89f5ca014a0/plugins/chemical-engineering-skills/skills/aspen-plus-operations/scripts/aspen_run_supervisor.py)及[唯一原生证据审查器](https://github.com/milklong888/chemical-engineering-skills/blob/98a2ea53a127cad7e2fecd0df447a89f5ca014a0/plugins/chemical-engineering-skills/skills/aspen-plus-operations/scripts/aspen_evidence.py)，按当前安装核接口和资源规则。本包不复制它们，不开COM、不联网、不把无错警句子转换成数字全零矩阵。

`SOURCE_METADATA.json`记录本包代码、测试、示例字节身份与验证范围。合成测试只证明对应离线检查行为，不代表Aspen实际执行、反应器/PSA能力或工程接受；原项目的谱系与资格不因公开此参考包而改变。
