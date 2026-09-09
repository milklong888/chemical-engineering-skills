# V10 离线分发边界

可用：39 章导航、6415 原细节 ID，其中 6392 原细节正文可查。另 23 项保留 ID 和原来源哈希、待逐项来源表达复核。不可用：571 整页原文、原 PDF、章节全文摘录。原生成说明完整保留在 `README.original.md`；其中 6986 条和全文检索等描述针对原本机资料，不是本发行覆盖声明。

统一入口：`../scripts/query_knowledge.py`；原始命令行也可查询包内现有细节：

```text
python knowledge/aspen_v10/scripts/query_user_guide_knowledge.py Wegstein --scope details --json
```

原查询不联网，原查询结果中的源摘录路径只是定位，未随包。正式跨版本操作仍须服从当前 Aspen 版本和当前项目依据。构建脚本保留供自备合法原件后维护使用，不要在已发布知识树中直接重建混入原页。
