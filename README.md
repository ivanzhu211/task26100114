# adcheck — 广告文案敏感词检查库

在保存流程前调用，拦截广告标题、正文、行动按钮中的敏感内容。
词典保存在本地 JSON 文件，检查状态仅存在于单次调用内，不保存被检查的文案。

## 词典格式

本地 JSON 文件，顶层为规则数组。每条规则包含唯一编号 `id`、词条 `term`，
以及匹配模式 `mode`（`substring` 子串 / `word` 整词）：

```json
[
  {"id": "r1", "term": "as", "mode": "substring"},
  {"id": "r2", "term": "wire transfer required", "mode": "word"}
]
```

## 使用方式

```python
from adcheck import Checker

checker = Checker.from_json("dictionary.json")  # 预加载，可长期复用

hits = checker.check({
    "title": title,
    "body": body,
    "cta": cta,
})

for hit in hits:
    print(hit.rule_id, hit.field, hit.start, hit.end)
    # 高亮原文：text[hit.start:hit.end]
```

- `Checker.from_json(path)` 或 `Checker(rules)` 构造检查器；`load_dictionary(path)` 仅装载规则。
- `check(fields)` 批量检查若干独立字段，字段之间绝不拼接匹配；返回全部 `Hit`。
- `Hit` 含 `rule_id`、`field`、`start`、`end`；位置按 Unicode 码点从 0 计数，终点不含。

## 比较规则

词条与文案按相同规则归一化后比较：

1. U+FF01–U+FF5E 映射为对应 ASCII，U+3000 映射为空格；
2. Unicode casefold；
3. 删除 U+200B 与 U+FEFF；
4. 连续空白（`str.isspace` 判定）折叠为一个 ASCII 空格，不去掉首尾空白。

整词模式要求归一化文本中命中两端的相邻字符不属于 Unicode 类别 L、M、N、Pc，
字段边缘视为有效边界。

## 命中与高亮语义

- 返回全部命中：包括重叠、包含、同一起点不同长度的命中；不同编号规则分别报告。
- 同一规则在同一字段映射到完全相同的原文范围时只报告一次。
- 高亮取覆盖命中来源的最短连续原文区间：一个原字符展开成多个比较字符时，
  命中任何部分都覆盖整个原字符；命中折叠空白时覆盖参与折叠的全部原空白；
  被删除的隐藏字符仅在命中两端之间时纳入范围。

## 运行测试

```sh
python3 -m unittest discover -s tests -v
```
