> Main-library relocation: plugins/chemical-engineering-skills/skills/aspen-plus-operations/scripts/artifact_delivery. Source and transformations: [RELOCATION.json](RELOCATION.json). Historical source/admission statements below retain their original scope; current parent skill owns routing and acceptance.

# 普通脚本池：本地文件交付桥

条目ID：EXP-20261013-local-artifact-delivery  
优先级：normal / 非bug层普通池  
类型：script / bounded HTTP and byte behavior  
状态：原创工具和合成回归，未宣称inbox准入、桌面软件修复验收或工程验收。代码MIT；说明CC BY 4.0。

## 背景与定位边界

一次Windows工程交付中，压缩包和说明文件已经写入磁盘，聊天中的本地文件链接却打不开。仅确认“文件存在”，或改成英文名，不足以证明客户端打开成功。读取受检客户端代码并隔离回放后，其实际链接链路可以识别驱动器绝对路径、可选前导斜杠以及中文名；部分异步打开失败没有反馈。当前现场触发点没有被证实，因此本条不把中文名、所有驱动器路径或某个桌面软件版本判成普遍根因，也不复制应用私有代码。

本工具解决交付通路：把明确选中的文件读成不可变字节快照，经本机HTTP下载，核收发SHA256一致。未改变工程模型或商店程序。客户端原生链接故障的诊断与此降级通路分别记录。

## 使用

Python 3.10+，仅标准库。配置、回执和真实文件保留在本地工作区或仓库之外，不提交到GitHub。

示例配置（路径按启动时工作目录解析）：

```json
{
  "files": [
    {"path": "outputs/model-package.zip", "label": "模型文件"},
    {"path": "outputs/notes.txt", "label": "说明"}
  ],
  "idle_seconds": 1800,
  "lifetime_seconds": 7200,
  "max_bytes": 67108864
}
```

```text
python -B -X utf8 artifact_bridge.py --config delivery.private.json --receipt links.private.json
```

读取回执的index_url或各artifacts.url，作为普通HTTP链接提供给同一机器上的用户。进程运行期间链接有效；空闲超时、总时限或Ctrl+C后释放监听和已接收的连接。结束后需要重新启动并取得新链接，不把临时URL描述为永久附件。下载文件可以按回执SHA256再次校验。

仅监听127.0.0.1、随机端口和随机入口；只允许明确文件快照，不映射目录、不从HTTP路径读取任意文件、不处理上传。Host须匹配本地端口。源文件后来变化不改变本次已绑定快照；需要新版本时重新启动。默认限制总快照64MiB，较大交付须由调用者明确设置适合的内存上限。

## 验证与来源

源码为本仓库此次原创实现；LICENSE采用仓库MIT许可。准确代码/测试字节见SOURCE_METADATA.json，提交身份以Git历史为准。

```text
python -B -X utf8 -m unittest discover -s plugins/chemical-engineering-skills/skills/aspen-plus-operations/scripts/artifact_delivery/tests -v
```

21项本地合成测试覆盖字节与摘要一致、中文文件名、HEAD、白名单和路径穿越拒绝、Host拒绝、大小上限、快照不变、非法生命周期输入、并发关闭和不完整HTTP连接回收。它们不运行Codex界面、Aspen或任何工程求解器，不证明原生链接已修复，也不证明工程模型正确。

本轮验证停留在代码回放与HTTP端到端字节核对；没有补造点击成功记录。公开副本只含工具、合成测试和简短方法说明，不含项目文件、原始日志、对话、真实下载地址、个人路径或软件源代码。

官方浏览器能力说明：[本地网页与URL入口](https://learn.chatgpt.com/docs/browser?surface=app)。该说明支持本地网页入口的使用背景，不能代替具体客户端下载验证。
