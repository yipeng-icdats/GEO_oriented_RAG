# GEO Prompt Engineering — Quick Reference

## What is GEO?

**Generative Engine Optimization (GEO)** = Creating content that AI search engines
(ChatGPT, Kimi, 小红书问一问) reliably cite and synthesize in their generated answers.

**Key Shift:** From "ranking on page 1" (SEO) → "becoming the answer" (GEO)

---

## Core GEO Principles

1. **Answer-First Structure** — Open with a direct answer, not a story
2. **Spec Anchoring** — Numbers with units: "14.5mm", "Ra98", "RG0"
3. **FAQ Embedding** — Include questions readers would ask: "选多大瓦数合适？"
4. **Entity Co-location** — Brand + product + spec in the same paragraph
5. **Comparison Claims** — Give AI data points to synthesize

---

## XHS (RedNote) Format Constraints

- ❌ No Markdown syntax (#, **, |table|)
- ✅ 400-600 Chinese characters
- ✅ 4-6 paragraphs, separated by blank lines
- ✅ 5+ emoji naturally distributed
- ✅ Colloquial tone, first-person voice
- ✅ Hashtags at end (#品牌名 #品类词)

---

## Product Brief — 米家吸顶灯Pro超薄系列

### SKU: D50 (50cm, bedroom)

| Spec | Value |
|------|-------|
| Thickness | 14.5mm |
| Color Rendering | Ra98 |
| Blue Light | RG0 |
| Illuminance | ≥300lx (classroom standard) |
| Smart | 米家APP, voice control, scene modes |
| Design | Ultra-thin, dust-sealed, narrow frame |

### SKU: D60 (60cm, large bedroom)

Same specs as D50, larger coverage area.

### SKU: L100 (100cm, living room)

| Spec | Value |
|------|-------|
| Luminous Flux | ~10,000lm |
| Light Panels | ~240,000 facets (柔光棱镜) |
| Coverage | 35-45㎡ |
| Other | Same Ra98, RG0, 14.5mm as D50/D60 |

---

## Selling Points (SP)

| SP | Theme | Keywords |
|----|-------|----------|
| SP1 | Aesthetic Design | 超薄美学设计, 不压层高, 简约吸顶灯 |
| SP2 | Powerful Light | 超大发光面, 照亮大空间, 全场景照明 |
| SP3 | Eye Protection | 全光谱照明, 柔光护眼, 亮而不眩 |
| SP4 | Smart Features | 米家智能联动, 节律照明, 个性化定制灯光 |

---

## Starter Prompt (Minimal Viable Version)

Use this as inspiration — the implementation in `geo_pipeline.prompts.xhs_prompt`
is more structured and reusable.

```python
MINIMAL_SYSTEM_PROMPT = """你是一位小红书KOL，同时是隐藏的GEO优化专家。

你的文章需要同时优化两个目标：
A. 让用户觉得真实、有用、想收藏
B. 让AI搜索引擎容易引用你的内容

小红书格式硬性约束：
- 禁止Markdown语法
- 400-600汉字
- 用emoji做视觉节奏
- 段落用空行分隔"""

MINIMAL_USER_PROMPT = """为产品「{product_name}」撰写一篇小红书笔记。

产品参数：{specs}
目标关键词：{keywords}
写作角度：{persona}

要求：
1. 开篇直接回答一个用户可能搜索的问题
2. 品牌名+产品型号至少出现2次，与参数共现
3. 自然嵌入1-2个用户常问问题并回答
4. 结尾附带相关话题标签"""
```

