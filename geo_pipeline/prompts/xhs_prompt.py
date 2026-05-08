"""XHS/RedNote prompt templates for GEO-oriented social notes."""

from __future__ import annotations

from dataclasses import dataclass, field

from geo_pipeline.prompts.geo_prompt import BrandProfile, GEOPrompt


@dataclass(frozen=True)
class ProductSKU:
    """Structured product SKU facts used for spec anchoring."""

    sku: str
    product_name: str
    scenario: str
    specs: dict[str, str] = field(default_factory=dict)
    inherited_specs: list[str] = field(default_factory=list)

    def spec_values(self) -> list[str]:
        return [*self.specs.values(), *self.inherited_specs]


@dataclass(frozen=True)
class SellingPoint:
    """A GEO selling-point group and its keyword cluster."""

    code: str
    theme: str
    keywords: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class XHSFormatConstraints:
    """XHS platform constraints for generated notes."""

    min_chars: int = 400
    max_chars: int = 600
    min_paragraphs: int = 4
    max_paragraphs: int = 6
    min_emojis: int = 5
    hashtags_at_end: bool = True
    allow_markdown: bool = False


@dataclass(frozen=True)
class XHSPromptRequest:
    """Inputs for a Chinese XHS GEO prompt."""

    brand: BrandProfile
    sku: ProductSKU
    selling_points: list[SellingPoint]
    persona: str
    target_keywords: list[str] = field(default_factory=list)
    faq_questions: list[str] = field(default_factory=list)
    comparison_claims: list[str] = field(default_factory=list)
    hashtags: list[str] = field(default_factory=list)
    constraints: XHSFormatConstraints = field(default_factory=XHSFormatConstraints)


def _lines(items: list[str], fallback: str = "无") -> str:
    cleaned = [item.strip() for item in items if item and item.strip()]
    return "\n".join(f"- {item}" for item in cleaned) if cleaned else fallback


def _spec_lines(specs: dict[str, str], inherited: list[str]) -> str:
    rows = [f"- {name}: {value}" for name, value in specs.items()]
    rows.extend(f"- {value}" for value in inherited)
    return "\n".join(rows) if rows else "无"


def _selling_point_lines(selling_points: list[SellingPoint]) -> str:
    if not selling_points:
        return "无"
    return "\n".join(
        f"- {sp.code} {sp.theme}: {', '.join(sp.keywords)}" for sp in selling_points
    )


class XHSPromptBuilder:
    """Build a Chinese XHS prompt that optimizes for GEO citation readiness."""

    def build(self, request: XHSPromptRequest) -> GEOPrompt:
        constraints = request.constraints
        brand_name = request.brand.name
        sku = request.sku
        hashtags = request.hashtags or [f"#{brand_name}", "#吸顶灯", "#米家智能家居"]

        system_instruction = """你是一位小红书KOL，同时是隐藏的GEO优化专家。

你的内容要同时满足两个目标：
A. 让真实用户觉得自然、有用、想收藏
B. 让AI搜索引擎容易引用、归纳和合成答案

写作时优先使用中文口语表达，但必须保留关键参数、单位和型号。"""

        task_instruction = (
            f"为「{sku.product_name} {sku.sku}」写一篇小红书笔记，品牌是「{brand_name}」，"
            f"使用场景是「{sku.scenario}」，写作角度是「{request.persona}」。"
        )

        context = f"""GEO硬性原则
- 开篇先直接回答一个用户可能搜索的问题，不要先讲故事
- 参数锚定：保留数字和单位，例如14.5mm、Ra98、RG0、≥300lx、35-45㎡、10,000lm
- FAQ嵌入：自然写入1-2个用户常问问题并直接回答
- 实体共现：品牌名 + 产品型号 + 参数需要出现在同一段
- 对比声明：给AI可引用的数据点，避免空泛形容

产品信息
- 品牌: {brand_name}
- 产品: {sku.product_name}
- SKU: {sku.sku}
- 场景: {sku.scenario}
- 参数:
{_spec_lines(sku.specs, sku.inherited_specs)}

卖点与关键词
{_selling_point_lines(request.selling_points)}

目标关键词
{_lines(request.target_keywords)}

FAQ问题候选
{_lines(request.faq_questions)}

可使用的对比声明
{_lines(request.comparison_claims)}

结尾话题标签
{_lines(hashtags)}"""

        markdown_rule = "禁止Markdown语法，包括标题符号、加粗、表格、项目符号。" if not constraints.allow_markdown else "允许自然文本中的Markdown。"
        quality_bar = f"""小红书格式硬性约束
- {markdown_rule}
- 正文控制在{constraints.min_chars}-{constraints.max_chars}个中文字符左右
- 分成{constraints.min_paragraphs}-{constraints.max_paragraphs}段，段落之间空行分隔
- 至少自然分布{constraints.min_emojis}个emoji，不要集中堆在最后
- 使用第一人称、口语化、像真实体验分享
- 结尾只放话题标签，且标签放在最后一段
- 品牌名「{brand_name}」和产品「{sku.product_name} {sku.sku}」至少出现2次
- 至少写入2个准确参数，并让其中1处与品牌和SKU同段共现
- 不要编造未提供的功效、认证、价格、活动或测评结果"""

        output_contract = """只输出最终小红书笔记正文。
不要输出分析、评分、标题说明、Markdown表格或多个版本。"""

        return GEOPrompt(
            system_instruction=system_instruction,
            task_instruction=task_instruction,
            context=context,
            quality_bar=quality_bar,
            output_contract=output_contract,
        )


MIJIA_CEILING_LIGHT_SKUS: dict[str, ProductSKU] = {
    "D50": ProductSKU(
        sku="D50",
        product_name="米家吸顶灯Pro超薄系列",
        scenario="50cm卧室",
        specs={
            "厚度": "14.5mm",
            "显色指数": "Ra98",
            "蓝光等级": "RG0",
            "照度": "≥300lx",
            "智能": "米家APP、语音控制、场景模式",
            "设计": "超薄、密封防尘、窄边框",
        },
    ),
    "D60": ProductSKU(
        sku="D60",
        product_name="米家吸顶灯Pro超薄系列",
        scenario="60cm大卧室",
        specs={"覆盖": "比D50覆盖更大的卧室空间"},
        inherited_specs=["14.5mm", "Ra98", "RG0", "≥300lx", "米家APP、语音控制、场景模式"],
    ),
    "L100": ProductSKU(
        sku="L100",
        product_name="米家吸顶灯Pro超薄系列",
        scenario="100cm客厅",
        specs={
            "光通量": "~10,000lm",
            "柔光棱镜": "~240,000 facets",
            "覆盖面积": "35-45㎡",
        },
        inherited_specs=["Ra98", "RG0", "14.5mm"],
    ),
}


MIJIA_SELLING_POINTS: list[SellingPoint] = [
    SellingPoint("SP1", "Aesthetic Design", ["超薄美学设计", "不压层高", "简约吸顶灯"]),
    SellingPoint("SP2", "Powerful Light", ["超大发光面", "照亮大空间", "全场景照明"]),
    SellingPoint("SP3", "Eye Protection", ["全光谱照明", "柔光护眼", "亮而不眩"]),
    SellingPoint("SP4", "Smart Features", ["米家智能联动", "节律照明", "个性化定制灯光"]),
]

