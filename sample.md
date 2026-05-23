下面详细讲解 Question-focused Vector Search + Context-aware Vector Search → Merge TopK Candidates 应该怎么做。

你可以把它理解成：

先从两个不同视角各找一批候选 FAQ / Answer Asset，然后把它们合并、去重、归一化、加权排序，选出一批最值得送入 reranker 的候选。

⸻

1. 为什么需要 Merge TopK Candidates？

因为你有两种 embedding：

A. Question-focused Vector

关注的是：

用户到底在问什么？

例如：

User Query:
How do I change my mobile number?
Question-focused FAQ:
How can I update my registered mobile number?

它擅长找到语义相似的问题。

⸻

B. Context-aware Vector

关注的是：

这个问题属于哪个产品、渠道、客户类型、业务范围？

例如：

Product / Service: Credit Card
Channel: Mobile App
Question: How can I update my registered mobile number?
Scope: Credit card customers

它擅长防止：

问题很像，但业务场景错了

⸻

所以两路召回结果可能是这样的：

Question-focused Search TopK:
1. FAQ_001: update online banking mobile number
2. FAQ_002: update credit card mobile number
3. FAQ_003: update corporate banking contact number
Context-aware Search TopK:
1. FAQ_002: update credit card mobile number
2. FAQ_004: credit card profile maintenance
3. FAQ_001: update online banking mobile number

你不能简单只取其中一路，也不能直接把两个列表拼接起来。你需要做 Merge TopK Candidates。

⸻

2. Merge TopK 的核心目标

Merge 的目标不是最终决定答案，而是选出一批高质量候选，交给后面的 reranker 和 decision logic。

也就是说：

Vector Search = 召回候选
Merge TopK = 整理候选
Reranker = 精排候选
Decision Logic = 判断是否直接返回 / 多候选 / fallback RAG

完整流程是：

User Query
  ↓
Question-focused Vector Search TopK_A
  +
Context-aware Vector Search TopK_B
  ↓
Merge / Deduplicate / Normalize / Boost
  ↓
Merged TopK Candidates
  ↓
Reranker
  ↓
Decision Logic

⸻

3. Merge TopK 的推荐步骤

建议按 7 步处理：

Step 1: 分别召回 TopK_A 和 TopK_B
Step 2: 按 answer_asset_id 去重
Step 3: 分数归一化
Step 4: 合并多路分数
Step 5: metadata boost / penalty
Step 6: 多样性控制，避免重复候选
Step 7: 截取 merged_top_k，送入 reranker

⸻

4. Step 1：分别召回 TopK_A 和 TopK_B

建议：

Question-focused Vector Search: top_k = 20 ~ 50
Context-aware Vector Search: top_k = 20 ~ 50
Merged TopK for reranker: 10 ~ 30

例如：

question_results = vector_search(
    index="faq_question_vector",
    query_embedding=query_embedding,
    top_k=30
)
context_results = vector_search(
    index="faq_context_vector",
    query_embedding=query_embedding,
    top_k=30
)

如果用户问题非常明确，可以只查 A，或者让 B 的权重较低。

如果用户问题很短、很泛、很容易歧义，就应该查 A + B。

⸻

5. Step 2：按 answer_asset_id 去重

两路召回可能命中同一个 FAQ。

例如：

A Search:
FAQ_001 score=0.87
B Search:
FAQ_001 score=0.81

这不是两个候选，而是同一个候选的两个信号。

所以要聚合到同一个对象：

{
  "answer_asset_id": "FAQ_001",
  "question_score": 0.87,
  "context_score": 0.81,
  "hit_sources": ["question", "context"]
}

⸻

6. Step 3：分数归一化

不同 vector index 的分数不一定完全可比。

例如：

Question-focused score 分布：0.75 ~ 0.92
Context-aware score 分布：0.60 ~ 0.84

如果直接加权，可能会偏向某一路。

建议做归一化。

常见方式有三种：

⸻

方式 A：Min-Max Normalize

适合简单实现。

normalized_score = (score - min_score) / (max_score - min_score)

缺点是：

容易受极端值影响

⸻

方式 B：Rank-based Score

更稳。

不太关心原始分数，只关心排名。

rank_score = 1 / rank

例如：

rank 1 → 1.0
rank 2 → 0.5
rank 3 → 0.333

也可以用更平滑的：

rank_score = 1 / sqrt(rank)

⸻

方式 C：RRF，Reciprocal Rank Fusion

这是多路召回合并中非常常用、非常稳的方式。

公式：

RRF score = Σ 1 / (k + rank_i)

其中：

rank_i = 候选在第 i 路检索结果中的排名
k = 平滑常数，常用 60

例如：

FAQ_001 在 A 中 rank 1，在 B 中 rank 5
RRF = 1 / (60 + 1) + 1 / (60 + 5)

RRF 的好处：

不依赖不同检索器的原始分数是否可比
对多路召回非常稳
排名靠前的候选自然加分
同时被多路召回的候选自然加分

我建议你们生产系统优先使用：

RRF + metadata boost + reranker

而不是简单把两个 vector score 相加。

⸻

7. Step 4：合并多路分数

推荐两种方案。

⸻

方案一：加权分数融合

适合你们已经对两路 score 做过归一化。

merged_score = (
    0.60 * question_score_norm
    + 0.30 * context_score_norm
    + 0.10 * metadata_match_score
)

适合场景：

两路分数稳定
向量库返回 score 可解释
你们有评估集可以调权重

⸻

方案二：RRF 融合

适合生产早期，更稳。

merged_score = (
    rrf_score
    + metadata_boost
    - metadata_penalty
)

适合场景：

刚上线
不同 index 分数不可比
想减少调参成本
召回结果来自多种方式：BM25、vector、context vector

我更推荐你们先用 RRF。

⸻

8. Step 5：metadata boost / penalty

Merge 不是只看语义，也要考虑业务适配度。

例如用户问题识别出：

{
  "language": "en",
  "product_or_service": "Credit Card",
  "channel": "Mobile App",
  "customer_segment": "Retail Customer"
}

候选 FAQ 有 metadata：

{
  "language": "en",
  "product_or_service": "Credit Card",
  "channel": "Mobile App",
  "customer_segment": "Retail Customer",
  "effective_status": "valid"
}

那么可以加分。

如果候选是：

{
  "product_or_service": "Corporate Banking"
}

就应该扣分甚至过滤掉。

⸻

metadata 处理建议

分两类：

A. Hard Filter

不满足就直接排除：

effective_status != valid
权限不允许
语言完全不支持
文档已过期
业务线不可见

B. Soft Boost / Penalty

不完全匹配但不一定排除：

product match +0.05
channel match +0.03
customer segment match +0.03
language match +0.05
risk too high -0.05
scope mismatch -0.10

⸻

9. Step 6：多样性控制

如果 TopK 里全是非常相似的 FAQ，会浪费 reranker 预算。

例如：

FAQ_001: How to update mobile number?
FAQ_002: How to change mobile number?
FAQ_003: How to modify phone number?

它们可能本质是重复问题。

建议做：

同一个 canonical_question_cluster 只保留最高分的 1~2 条
同一个 source_doc section 不要保留过多条
明显重复的 answer_asset 进入 deduplicate 逻辑

简单规则：

same question_cluster_id: max 2
same source_doc_id + section_id: max 3

这样 reranker 能看到更丰富的候选。

⸻

10. Step 7：截取 merged_top_k

最后输出：

merged_top_k = 20

交给 reranker。

推荐参数：

场景	A top_k	B top_k	merged_top_k	reranker top_n
小型 FAQ 库	20	20	10	5
中型 FAQ 库	30	30	20	5-10
大型 FAQ 库	50	50	30	10
高风险场景	50	50	30	10 + strict rules

⸻

11. Python 参考代码：完整 Merge TopK 实现

下面是一份可以直接改造成你们项目代码的版本。

11.1 数据结构

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Any
from collections import defaultdict
import math
@dataclass
class SearchResult:
    answer_asset_id: str
    score: float
    rank: int
    source: str  # "question", "context", "bm25" 等
    metadata: Dict[str, Any] = field(default_factory=dict)
@dataclass
class MergedCandidate:
    answer_asset_id: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    question_score: Optional[float] = None
    question_rank: Optional[int] = None
    context_score: Optional[float] = None
    context_rank: Optional[int] = None
    bm25_score: Optional[float] = None
    bm25_rank: Optional[int] = None
    hit_sources: Set[str] = field(default_factory=set)
    rrf_score: float = 0.0
    metadata_score: float = 0.0
    final_merge_score: float = 0.0

⸻

11.2 Hard Filter

def pass_hard_filters(
    candidate_metadata: Dict[str, Any],
    query_context: Dict[str, Any]
) -> bool:
    """
    Hard filters: 不满足就不允许进入候选池。
    """
    # 1. 答案资产必须有效
    if candidate_metadata.get("effective_status") != "valid":
        return False
    # 2. 权限必须允许
    user_permissions = set(query_context.get("user_permissions", []))
    required_permissions = set(candidate_metadata.get("required_permissions", []))
    if required_permissions and not required_permissions.issubset(user_permissions):
        return False
    # 3. 语言策略
    # 如果系统要求必须同语言返回，则不同语言可直接过滤。
    query_language = query_context.get("language")
    candidate_language = candidate_metadata.get("language")
    if query_context.get("strict_language_match", True):
        if query_language and candidate_language and query_language != candidate_language:
            return False
    # 4. 文档不能过期
    if candidate_metadata.get("source_doc_status") == "expired":
        return False
    return True

⸻

11.3 Metadata Soft Score

def calculate_metadata_score(
    candidate_metadata: Dict[str, Any],
    query_context: Dict[str, Any]
) -> float:
    """
    Soft boost / penalty.
    返回值建议控制在 -0.20 ~ +0.20 之间，避免盖过语义召回。
    """
    score = 0.0
    # Language match
    if candidate_metadata.get("language") == query_context.get("language"):
        score += 0.04
    # Product / Service match
    if candidate_metadata.get("product_or_service") == query_context.get("product_or_service"):
        score += 0.06
    elif query_context.get("product_or_service") and candidate_metadata.get("product_or_service"):
        score -= 0.06
    # Channel match
    if candidate_metadata.get("channel") == query_context.get("channel"):
        score += 0.03
    elif query_context.get("channel") and candidate_metadata.get("channel"):
        score -= 0.03
    # Customer segment match
    if candidate_metadata.get("customer_segment") == query_context.get("customer_segment"):
        score += 0.03
    elif query_context.get("customer_segment") and candidate_metadata.get("customer_segment"):
        score -= 0.03
    # Risk penalty
    risk_level = candidate_metadata.get("risk_level")
    if risk_level == "high":
        score -= 0.05
    # Source type boost
    source_type = candidate_metadata.get("source_type")
    if source_type in {"official_faq", "script", "golden_answer"}:
        score += 0.04
    elif source_type == "runtime_cache":
        score -= 0.05
    # Clamp
    return max(-0.20, min(0.20, score))

⸻

11.4 RRF 计算

def reciprocal_rank_fusion_score(
    ranks: List[Optional[int]],
    k: int = 60
) -> float:
    """
    RRF score.
    ranks 中可以包含 None，表示该候选没有被某一路召回。
    """
    score = 0.0
    for rank in ranks:
        if rank is not None:
            score += 1.0 / (k + rank)
    return score

⸻

11.5 Merge TopK 主函数

def merge_topk_candidates(
    question_results: List[SearchResult],
    context_results: List[SearchResult],
    query_context: Dict[str, Any],
    merged_top_k: int = 20,
    rrf_k: int = 60,
    max_per_cluster: int = 2,
    max_per_section: int = 3
) -> List[MergedCandidate]:
    """
    Merge Question-focused Vector Search 和 Context-aware Vector Search 的结果。
    主要步骤：
    1. 合并两路结果
    2. 按 answer_asset_id 去重
    3. hard filter
    4. RRF 融合
    5. metadata boost / penalty
    6. 多样性控制
    7. 返回 merged_top_k
    """
    candidate_map: Dict[str, MergedCandidate] = {}
    all_results = question_results + context_results
    for result in all_results:
        asset_id = result.answer_asset_id
        if asset_id not in candidate_map:
            candidate_map[asset_id] = MergedCandidate(
                answer_asset_id=asset_id,
                metadata=result.metadata
            )
        candidate = candidate_map[asset_id]
        candidate.hit_sources.add(result.source)
        # 如果两路结果里 metadata 有差异，可以做合并。
        # 这里简单以后出现的 metadata 补充已有 metadata。
        candidate.metadata.update(result.metadata)
        if result.source == "question":
            candidate.question_score = result.score
            candidate.question_rank = result.rank
        elif result.source == "context":
            candidate.context_score = result.score
            candidate.context_rank = result.rank
        elif result.source == "bm25":
            candidate.bm25_score = result.score
            candidate.bm25_rank = result.rank
    filtered_candidates: List[MergedCandidate] = []
    for candidate in candidate_map.values():
        if not pass_hard_filters(candidate.metadata, query_context):
            continue
        candidate.rrf_score = reciprocal_rank_fusion_score(
            ranks=[
                candidate.question_rank,
                candidate.context_rank,
                candidate.bm25_rank
            ],
            k=rrf_k
        )
        candidate.metadata_score = calculate_metadata_score(
            candidate.metadata,
            query_context
        )
        # 双路命中奖励：说明 question 和 context 都认为它相关
        multi_source_boost = 0.0
        if len(candidate.hit_sources) >= 2:
            multi_source_boost = 0.015
        candidate.final_merge_score = (
            candidate.rrf_score
            + candidate.metadata_score
            + multi_source_boost
        )
        filtered_candidates.append(candidate)
    # 初步排序
    filtered_candidates.sort(
        key=lambda x: x.final_merge_score,
        reverse=True
    )
    # 多样性控制
    diversified = diversify_candidates(
        candidates=filtered_candidates,
        max_per_cluster=max_per_cluster,
        max_per_section=max_per_section
    )
    return diversified[:merged_top_k]

⸻

11.6 多样性控制函数

def diversify_candidates(
    candidates: List[MergedCandidate],
    max_per_cluster: int = 2,
    max_per_section: int = 3
) -> List[MergedCandidate]:
    """
    避免 merged TopK 被同一个问题簇或同一个 section 占满。
    """
    cluster_count = defaultdict(int)
    section_count = defaultdict(int)
    diversified = []
    for candidate in candidates:
        cluster_id = candidate.metadata.get("question_cluster_id")
        section_id = candidate.metadata.get("section_id")
        source_doc_id = candidate.metadata.get("source_doc_id")
        section_key = f"{source_doc_id}:{section_id}"
        if cluster_id and cluster_count[cluster_id] >= max_per_cluster:
            continue
        if section_id and section_count[section_key] >= max_per_section:
            continue
        diversified.append(candidate)
        if cluster_id:
            cluster_count[cluster_id] += 1
        if section_id:
            section_count[section_key] += 1
    return diversified

⸻

12. 示例：模拟两路搜索结果合并

question_results = [
    SearchResult(
        answer_asset_id="FAQ_001",
        score=0.89,
        rank=1,
        source="question",
        metadata={
            "effective_status": "valid",
            "language": "en",
            "product_or_service": "Personal Online Banking",
            "channel": "Mobile App",
            "customer_segment": "Retail",
            "source_type": "official_faq",
            "risk_level": "medium",
            "question_cluster_id": "CLUSTER_PHONE_UPDATE",
            "source_doc_id": "DOC_001",
            "section_id": "PROFILE"
        }
    ),
    SearchResult(
        answer_asset_id="FAQ_002",
        score=0.86,
        rank=2,
        source="question",
        metadata={
            "effective_status": "valid",
            "language": "en",
            "product_or_service": "Credit Card",
            "channel": "Mobile App",
            "customer_segment": "Retail",
            "source_type": "official_faq",
            "risk_level": "medium",
            "question_cluster_id": "CLUSTER_PHONE_UPDATE",
            "source_doc_id": "DOC_002",
            "section_id": "CARD_PROFILE"
        }
    ),
]
context_results = [
    SearchResult(
        answer_asset_id="FAQ_002",
        score=0.84,
        rank=1,
        source="context",
        metadata={
            "effective_status": "valid",
            "language": "en",
            "product_or_service": "Credit Card",
            "channel": "Mobile App",
            "customer_segment": "Retail",
            "source_type": "official_faq",
            "risk_level": "medium",
            "question_cluster_id": "CLUSTER_PHONE_UPDATE",
            "source_doc_id": "DOC_002",
            "section_id": "CARD_PROFILE"
        }
    ),
    SearchResult(
        answer_asset_id="FAQ_003",
        score=0.80,
        rank=2,
        source="context",
        metadata={
            "effective_status": "valid",
            "language": "en",
            "product_or_service": "Corporate Banking",
            "channel": "Web Portal",
            "customer_segment": "Corporate",
            "source_type": "official_faq",
            "risk_level": "medium",
            "question_cluster_id": "CLUSTER_PHONE_UPDATE",
            "source_doc_id": "DOC_003",
            "section_id": "CORP_PROFILE"
        }
    ),
]
query_context = {
    "language": "en",
    "product_or_service": "Credit Card",
    "channel": "Mobile App",
    "customer_segment": "Retail",
    "user_permissions": [],
    "strict_language_match": True
}
merged = merge_topk_candidates(
    question_results=question_results,
    context_results=context_results,
    query_context=query_context,
    merged_top_k=10
)
for c in merged:
    print(
        c.answer_asset_id,
        c.final_merge_score,
        c.rrf_score,
        c.metadata_score,
        c.hit_sources
    )

预期结果大概会是：

FAQ_002 排第一
FAQ_001 排第二
FAQ_003 排后面或被 metadata penalty 降权

因为：

FAQ_002 同时被 question 和 context 命中
FAQ_002 product/channel/customer segment 都匹配
FAQ_001 question 很像，但 product 不匹配
FAQ_003 context 有点像，但 customer segment 不匹配

⸻

13. 如果你想用加权 score 融合，而不是 RRF

可以这样写。

13.1 Normalize 函数

def min_max_normalize_results(
    results: List[SearchResult]
) -> Dict[str, float]:
    """
    对一路 search result 做 min-max normalize。
    返回 answer_asset_id -> normalized_score。
    """
    if not results:
        return {}
    scores = [r.score for r in results]
    min_score = min(scores)
    max_score = max(scores)
    if max_score == min_score:
        return {r.answer_asset_id: 1.0 for r in results}
    return {
        r.answer_asset_id: (r.score - min_score) / (max_score - min_score)
        for r in results
    }

⸻

13.2 Weighted Merge

def weighted_merge_topk_candidates(
    question_results: List[SearchResult],
    context_results: List[SearchResult],
    query_context: Dict[str, Any],
    merged_top_k: int = 20,
    question_weight: float = 0.65,
    context_weight: float = 0.25,
    metadata_weight: float = 0.10
) -> List[MergedCandidate]:
    question_norm = min_max_normalize_results(question_results)
    context_norm = min_max_normalize_results(context_results)
    candidate_map: Dict[str, MergedCandidate] = {}
    for result in question_results + context_results:
        asset_id = result.answer_asset_id
        if asset_id not in candidate_map:
            candidate_map[asset_id] = MergedCandidate(
                answer_asset_id=asset_id,
                metadata=result.metadata
            )
        candidate = candidate_map[asset_id]
        candidate.hit_sources.add(result.source)
        candidate.metadata.update(result.metadata)
        if result.source == "question":
            candidate.question_score = question_norm.get(asset_id, 0.0)
            candidate.question_rank = result.rank
        elif result.source == "context":
            candidate.context_score = context_norm.get(asset_id, 0.0)
            candidate.context_rank = result.rank
    final_candidates = []
    for candidate in candidate_map.values():
        if not pass_hard_filters(candidate.metadata, query_context):
            continue
        q_score = candidate.question_score or 0.0
        c_score = candidate.context_score or 0.0
        metadata_score = calculate_metadata_score(
            candidate.metadata,
            query_context
        )
        # metadata_score 原本在 -0.2 ~ 0.2，
        # 转成 0~1 附近的辅助分数。
        metadata_score_normalized = 0.5 + metadata_score
        candidate.final_merge_score = (
            question_weight * q_score
            + context_weight * c_score
            + metadata_weight * metadata_score_normalized
        )
        # 双路命中加一点点奖励
        if len(candidate.hit_sources) >= 2:
            candidate.final_merge_score += 0.03
        final_candidates.append(candidate)
    final_candidates.sort(
        key=lambda x: x.final_merge_score,
        reverse=True
    )
    return diversify_candidates(final_candidates)[:merged_top_k]

⸻

14. RRF vs Weighted Merge 怎么选？

推荐优先级

我建议：

第一版生产：RRF
有评估集之后：RRF + 少量 metadata boost
有足够日志之后：学习型融合 / LambdaMART / LTR

⸻

对比

方法	优点	缺点	推荐阶段
Weighted Score	直观，可控	依赖 score 可比性	有稳定评估集后
RRF	稳定，不依赖原始分数	不利用 score 绝对值	生产早期优先
Learning to Rank	效果潜力最好	需要标注数据和训练	成熟阶段

⸻

15. Merge TopK 后还要做什么？

Merge 只是中间步骤。

后面还要：

Merged TopK Candidates
  ↓
Reranker
  ↓
Business Rule Validation
  ↓
Decision Logic

Reranker 输入可以使用 rich candidate text：

Document Type: FAQ
Business Domain: Account Management
Product / Service: Credit Card
Channel: Mobile App
Customer Segment: Retail
Document Title: Credit Card FAQ
Section Title: Profile Maintenance
Applicable Scope: Credit card customers using Mobile App
Question:
How can I update my registered mobile number?
Alternative User Expressions:
- Change my phone number
- Update credit card mobile number
Key Constraints:
Only available for verified retail customers.
Answer Summary:
User can update the registered mobile number through Mobile App profile settings or branch verification depending on account status.

⸻

16. Decision Logic 示例

Merge 和 rerank 完成后，才判断是否直接返回。

from typing import Literal
RouteDecision = Literal[
    "DIRECT_ANSWER",
    "SHOW_MULTIPLE_CANDIDATES",
    "ASK_CLARIFICATION",
    "RAG_FALLBACK"
]
@dataclass
class RerankedCandidate:
    answer_asset_id: str
    rerank_score: float
    metadata: Dict[str, Any]
    answer_summary: str = ""
def decide_after_rerank(
    candidates: List[RerankedCandidate],
    risk_level: str = "medium"
) -> RouteDecision:
    if not candidates:
        return "RAG_FALLBACK"
    top1 = candidates[0]
    top2 = candidates[1] if len(candidates) > 1 else None
    thresholds = {
        "low": {
            "direct": 0.88,
            "fallback": 0.72,
            "gap": 0.06
        },
        "medium": {
            "direct": 0.92,
            "fallback": 0.78,
            "gap": 0.08
        },
        "high": {
            "direct": 0.96,
            "fallback": 0.85,
            "gap": 0.12
        }
    }
    t = thresholds.get(risk_level, thresholds["medium"])
    if top1.rerank_score < t["fallback"]:
        return "RAG_FALLBACK"
    if top2:
        gap = top1.rerank_score - top2.rerank_score
        # 多个候选都很强，且分差小
        if top1.rerank_score >= t["direct"] and top2.rerank_score >= t["fallback"] and gap < t["gap"]:
            if is_scope_conflict(top1, top2):
                return "ASK_CLARIFICATION"
            else:
                return "SHOW_MULTIPLE_CANDIDATES"
    if top1.rerank_score >= t["direct"]:
        if risk_level == "high":
            # 高风险场景还可以要求更严格的业务校验
            if not is_high_risk_auto_answer_allowed(top1):
                return "ASK_CLARIFICATION"
        return "DIRECT_ANSWER"
    return "ASK_CLARIFICATION"
def is_scope_conflict(
    c1: RerankedCandidate,
    c2: RerankedCandidate
) -> bool:
    """
    判断两个候选是否属于不同业务范围。
    """
    conflict_fields = [
        "product_or_service",
        "channel",
        "customer_segment",
        "business_domain"
    ]
    for field in conflict_fields:
        v1 = c1.metadata.get(field)
        v2 = c2.metadata.get(field)
        if v1 and v2 and v1 != v2:
            return True
    return False
def is_high_risk_auto_answer_allowed(
    candidate: RerankedCandidate
) -> bool:
    """
    高风险答案是否允许自动直接返回。
    """
    source_type = candidate.metadata.get("source_type")
    approval_status = candidate.metadata.get("approval_status")
    effective_status = candidate.metadata.get("effective_status")
    if effective_status != "valid":
        return False
    if source_type in {"official_faq", "script", "golden_answer"}:
        return True
    if approval_status == "human_approved":
        return True
    return False

⸻

17. 推荐的最终实现组合

我建议你们第一版这样实现：

1. Question-focused Search: Top 30
2. Context-aware Search: Top 30，仅在需要时启用
3. Hard Filter:
   - permission
   - effective_status
   - language
   - document status
4. Merge:
   - answer_asset_id 去重
   - RRF fusion
   - metadata boost / penalty
   - diversity control
5. 输出 Merged Top 20
6. Reranker 精排
7. Decision Logic:
   - Direct Answer
   - Multiple Candidates
   - Clarification
   - RAG Fallback

⸻

18. 一句话总结

Merge TopK Candidates 的关键不是简单拼接两个搜索结果，而是把 Question-focused 语义相似性、Context-aware 业务适用性、metadata 约束和多样性控制融合起来，形成一批“既相关、又可能适用、又值得精排”的候选。

推荐你们生产第一版优先使用：

RRF + hard filters + metadata boost + diversity control

等有真实评估集和线上日志后，再进一步优化成：

Weighted Fusion / Learning-to-Rank