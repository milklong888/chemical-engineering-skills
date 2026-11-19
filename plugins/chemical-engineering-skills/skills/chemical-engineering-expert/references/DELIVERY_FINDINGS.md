# 完整工程交付的审核问题

首版冻结的转化率、回收率、纯度、产量、取压点及净接口中，被确定为设计规定的项目，作为切岛优化和回装验收的约束。终审以同版实际结果核对它们。每个发现用稳定编号从原始审核跟到复核。

**运行位置。** 在相同的项目证据根调用 `expert_cli` 的 `design_stage`。公开入口将收到的源审、骨架审及正式交付审核里的原问题按原文及校验值保存到 `PROJECT_REVIEW_HISTORY/`。多位审核人可分别登记，重试对同一份审核只保留一份。历史记录也在阶段未通过时保留。旧项目在首次采用本流程时把仍相关的原审核转为带原出处的 `review_sources`。没有导入的历史，需要如实说明覆盖范围。

**冻结交付范围。** 在有 SHA-256 引用的项目依据内填写 `case_id` 和 `delivery_review`。其中 `preparer_id` 是主编制者，`scope` 列出约定交付项，`artifacts` 列实际交付文件，`evidence_refs` 列同次读回或更正后的依据。每份文件用 `{path,sha256}` 标识。`parents` 列前版或合并分支问题清单的位置，`review_sources` 列另外的专项、用户点名及历史审核。首版没有父版本时可填空数组。全流程项目绑定 `fullflow_contract`；已有源审及骨架审会从该合同取出。

**留存问题。** 补充审核记录用 `{case_id,task_revision,issues:[…]}`。每个问题保留 `id`、原意、出处和处理条件。可量化的问题在首次登记时附 `criteria`。例如某设计规定可写为 `{"path":"DEMO_OUT.pressure","unit":"bar","basis":"absolute","comparison":"eq","expected":24}`。这里的数值只展示字段。允许的比较是等于、至少或至多，对应 `eq/ge/le`。承诺的范围或允许偏差要在项目设计依据里事先明确。

**核对当前版本。** 项目根的 `PROJECT_REVIEW_FINDINGS.json` 保留 `case_id,task_revision,run_id,parents,review_sources,items,final_review_ref,invocation_ref`。其 `review_sources` 是另外登记的来源以及从本版合同提取的所有源审、骨架审原输出。每行 `items` 有 `id,status`。未解决项写 `next_action`；修复并复核写 `verified_fixed`；有证据驳回写 `evidence_refuted`。两种结案均要有独立复核。历史快照按编号与当前项取并集；不能通过新审核未提、换名或删除一行结案。

**独立终审。** 将本版实际成品、读回、原问题清单和验收范围交给独立审核人。保留该次真实调用。终审 JSON 带 `kind=final_delivery_review,case_id,task_revision,run_id,reviewer_id,call_id,scope,artifacts,checks,issues,finding_rechecks`。调用凭据有同一 `reviewer_id,call_id` 和 `output_sha256`。每个范围在 `checks` 有 `scope,observation,locator,evidence_ref`，已结案的每个编号在 `finding_rechecks` 有 `id,status,observation,locator,evidence_ref`。对 JSON 另附指定点路径的 `observed_value`，对原始文本引用连续 `excerpt`。定量复验文件含本版 `case_id,task_revision,run_id,artifact` 和 `results`；原判据指定路径上的对象含 `value,unit,basis`。工程判断要检查证据与结论的关系；程序能比对登记过的原文、数值和身份。

**怎么交付。** 正式全流程用 `design_stage / delivery`。如另行打包，交付模板的清单填 `formal_delivery:true` 和 `review_request`，后者沿用阶段的项目、修订、运行和依据引用。单独复制到项目的模板可用 `--runtime-root` 指向运行库。检查器同时核已冻结的清单和历史。只交用户明确索取的试跑件时，写明本次提供的文件、验证范围和遗留问题。工程核验、Aspen 精确文件实跑、用户确认完成、经验公开批准各自留自己的证据。

**冻结与逐项实读。** 交付候选就绪后，给 `delivery_review.scope_evidence` 中的每个范围列出一份或多份精确文件引用，并使每件成品都有归属。阶段入口用 `PROJECT_REVIEW_SCOPE_HISTORY.sqlite3` 保存当时的范围。一般规划无需未来成品的哈希。按工程依据正常滚版，保留同一设计义务；缩减用户已约定的范围须有原范围变更依据。终审的每一行都要读该范围下指定的文件。文本用 `L12` 这样的行号，Word 用 `PARA12` 段号，PDF 用物理页 `P5`；JSON 用点路径和相应值。BKP 等二进制的 `artifact_ref` 要与同一范围的可读 `evidence_ref` 对上，后者记录本次 `case_id,task_revision,run_id,artifact` 和实际 `results`，并核读具体字段。

**Aspen 原生文本。** 核查原始 `.his`、`.inp` 或 `.rep/.rpt` 时，`evidence_ref` 引用原文件，另给 `native_audit_ref`，用同次 v3 运行审计把读数锁定到无编辑精确复开的模型。模型、审计、原始输出及辅助凭据都列入冻结交付证据。历史和输入导出分别按该次审计内的原始文件核对路径、大小和 SHA-256，历史复用审计明确绑定的解码凭据。报告优先读取该审计里通过同次关联的 `sidecars` 行；用补充运行工具直接导出的报告，可引用实际生成报告的 `native_producer_ref`（现有 `<label>_streams_blocks.json` 格式），按运行号、原生输出目录、报告栏目和原始文件指纹核对。同一路径的审计记录有冲突时须回核原生证据。非 UTF-8 的输入导出或报告可补 `native_output_index_ref`。索引采用 `aspen-native-review-outputs-v1`，记录 `case_id,task_revision,run_id,model_ref,native_audit_ref,outputs`；相应条目带 `raw_ref` 与 `conversion:{codec,text_ref}`。转码件只提供解码依据，文件身份取自原运行记录。程序逐字核对 UTF-8 转码件、原始字节往返以及所引原文件行号。使用当前模型的读证可记录真实警告，工程验收仍按原规则判断。

**经批准的改动和部分交付。** 原问题可用 `scope` 声明影响的交付项。只交其中一个已授权子项时，其余范围的遗留保留原编号与下一步，范围不明的发现继续核对。设计规定发生有据变更时在冻结依据登记 `criterion_replacements`，回读变更表里的原编号、完整旧判据及新判据和批准来源。同一次修改只替换获准的判据。用新文件名、局部对比或另一份报告无法证明原指标已达到。
