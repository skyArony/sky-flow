---
name: dual-steelman
description: 'Use bidirectional steelmanning to turn a consequential, ambiguous, conflicted, or emotionally loaded question into a clear decision. Invoke when the user names $dual-steelman, asks to examine both sides, or seems unable to state the real decision, priorities, or trade-offs. Do not use for straightforward factual questions, routine implementation, or simple preferences.'
---

# 双向 steelman

帮助用户把“表面问题”变成真正需要决定的问题，并同时 steelman 相互竞争的方案，避免迎合用户原有立场或攻击弱版本的反方。

## 工作流

1. 识别用户真正想要的结果、可选方案、约束、时间尺度与风险。将问题重述为一句清晰的决策题；对缺失但会影响结论的上下文，列为假设而非擅自补全。
2. 分别为主要方案与最强替代方案做 steelman 论证。给出各自最合理的目标、最佳证据、收益、代价、失败模式和最难反驳的点。不要把任一方写成稻草人，也不要用虚假的对称性掩盖证据强弱。
3. 找出真正会改变结论的关键变量、未知事实或价值取舍。说明每种可能取值会如何改变选择。
4. 在明确假设下给出判断，不要只罗列利弊。说明理由、置信度、何时应改选另一方案，以及一个可执行的下一步。

## 输出形状

默认使用以下紧凑结构，并按问题复杂度合并或省略不必要部分：

```text
真实问题：<重述后的决策与成功标准>

方案 A 的最强 steelman：<最有力理由、证据与代价>
方案 B 的最强 steelman：<最有力理由、证据与代价>

决定变量：<会翻转结论的事实、约束或价值取舍>

判断与下一步：<条件化建议、理由、一个行动或一个关键追问>
```

## 边界

- 直接完成分析；除非用户明确要求，否则不要只返回可复制的 Prompt。
- 仅在一个答案会因其回答而明显翻转时，提出一个关键追问；否则用显式假设继续给出有用结论。
- 用户给出多个方案时，比较最有决策价值的方案；必要时先归并相近选项。
- 用户明显已有答案时，仍公平地 steelman 该答案的最强反面，而不是顺着用户立场。
