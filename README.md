# task26100114

## 广告文案敏感词检查库

纯 Python 库（仅标准库，Python 3.10+），由上层保存流程直接调用。词典保存在本地
JSON 文件，可预加载并复用；检查状态只在单次调用内存中存在，不保存被检查的文案。

### 快速开始

```python
from sensitive_words import Checker, Dictionary

dictionary = Dictionary.load("examples/dictionary.json")  # 预加载，可复用
checker = Checker(dictionary)

hits = checker.check({
    "title": title,   # 广告标题
    "body": body,     # 广告正文
    "cta": cta,       # 行动按钮
})

for hit in hits:
    text = fields[hit.field]
    print(hit.rule_id, hit.field, text[hit.start:hit.end])  # 原文高亮区间
```

`checker.check(fields)` 批量检查相互独立的字段（绝不跨字段拼接匹配），返回全部
命中 `Hit(rule_id, field, start, end)`。`start`/`end` 定位**原文**范围，按
Unicode 码点计数，从 0 开始，`end` 不包含在范围内，可直接用于高亮。命中按字段
给出顺序分组，字段内按 `(start, end, rule_id)` 排序。

### 词典格式

本地 JSON 文件，每条规则包含唯一编号、词条和匹配模式：

```json
{
  "rules": [
    {"id": "r1", "term": "as", "mode": "substring"},
    {"id": "r2", "term": "free money", "mode": "whole_word"}
  ]
}
```

- `id`：词典内唯一，重复会抛出 `ValueError`。
- `term`：词条，归一化后必须非空。
- `mode`：`"substring"`（可出现在任意位置）或 `"whole_word"`（整词）。

### 比较规则（词条与文案一致）

按顺序执行：

1. U+FF01–U+FF5E 映射为对应 ASCII 字符，U+3000 映射为空格；
2. Unicode casefold；
3. 删除 U+200B 与 U+FEFF；
4. 连续空白（按 `str.isspace` 判定）折叠为一个 ASCII 空格。

不去掉首尾空白，不做除此之外的字符等价转换。

### 匹配与高亮语义

- **整词模式**：归一化文本中命中两端的相邻字符均不属于 Unicode 类别
  L、M、N、Pc；字段边缘视为有效边界。
- **全部命中**：包括相互重叠、包含以及同一起点的不同长度命中；不同编号规则
  即使归一化后相同也分别报告；同一规则在同一字段映射到完全相同的原文范围时
  只报告一次。
- **高亮区间**：覆盖命中来源的最短连续原文区间。一个原字符展开成多个比较字符
  时，命中任意部分即覆盖整个原字符；命中折叠空白时覆盖参与折叠的全部原空白；
  被删除的隐藏字符仅在命中两端之间时纳入范围。

### 运行测试与示例

```sh
python3 -m unittest discover -s tests -v
python3 examples/check_copy.py
```

### 代码结构

- `sensitive_words/normalizer.py` — 归一化与原文位置映射
- `sensitive_words/dictionary.py` — 规则模型与 JSON 词典装载
- `sensitive_words/checker.py` — 批量字段检查与命中定位
- `tests/test_sensitive_words.py` — 自动化测试
- `examples/` — 示例词典与端到端示例
