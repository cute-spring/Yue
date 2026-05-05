# Bing CN MCP Real-World Test Checklist

This checklist is for the live `bing-cn-mcp-server` remote MCP service currently configured in Yue as:

```json
{
  "name": "bing-cn-mcp-server",
  "transport": "streamable_http",
  "url": "https://mcp.api-inference.modelscope.net/6ab3a144b1994a/mcp",
  "enabled": true
}
```

Use this checklist to verify that the service works in realistic Chinese-language scenarios rather than only toy queries.

## Scope

Validate both tools exposed by the service:

- `bing_search`
- `crawl_webpage`

Validate not only connectivity, but also:

- relevance
- freshness
- Chinese query handling
- multi-step search -> crawl flow
- stability across practical consumer scenarios

## Standard Execution Pattern

For each case:

1. Run `bing_search`
2. Review returned titles, snippets, and URLs
3. Select the top 1 to 3 most relevant results
4. Run `crawl_webpage` with:
   - `uuids`
   - `urlMap`
5. Judge whether the result is useful for a real user decision

Recommended search params unless otherwise noted:

```json
{
  "count": 5,
  "offset": 0
}
```

## Pass Criteria

A case is a practical pass when most of the following are true:

- Search returns non-empty results
- Results are clearly relevant to the query intent
- Results are reasonably fresh for time-sensitive topics
- Different results are not just duplicates from one low-quality source
- `crawl_webpage` returns usable body content for at least one relevant result
- A human could make a real decision based on the returned information

## Test Cases

### 1. Today Weather and Going Out

Purpose:
Validate local, time-sensitive, daily-use search behavior.

Search query:

```json
{
  "query": "上海 2026-05-02 天气 适合出门吗",
  "count": 5,
  "offset": 0
}
```

What to check:

- Whether results mention temperature, rain, or alerts
- Whether results look current rather than generic
- Whether a user could decide whether to bring an umbrella

Suggested crawl target:

- Top weather/news page

Expected practical outcome:

- Enough information to support a same-day outing decision

### 2. Today Headlines

Purpose:
Validate same-day general news discovery.

Search query:

```json
{
  "query": "2026-05-02 今日热点新闻 中国",
  "count": 8,
  "offset": 0
}
```

What to check:

- Whether results are from today or very recent
- Whether results represent different major events
- Whether snippets are informative enough to distinguish stories

Suggested crawl target:

- Top 2 news results

Expected practical outcome:

- Enough information to summarize what happened today

### 3. AI / Tech News Follow-up

Purpose:
Validate domain-specific news retrieval for a real research workflow.

Search query:

```json
{
  "query": "OpenAI 最新 新闻 2026-05-02",
  "count": 6,
  "offset": 0
}
```

What to check:

- Whether results are recent enough
- Whether the set includes media/blog/forum diversity
- Whether snippets identify distinct news items instead of repeating one story

Suggested crawl target:

- Most relevant 1 to 2 articles

Expected practical outcome:

- Enough information to brief someone on current AI news

### 4. Weekend Travel / Leisure Choice

Purpose:
Validate recommendation-style, fuzzy consumer intent.

Search query:

```json
{
  "query": "上海 周末 去哪里玩 适合情侣 2026-05",
  "count": 10,
  "offset": 0
}
```

What to check:

- Whether results match the couple/weekend scenario
- Whether results provide multiple meaningful options
- Whether content is useful beyond just listing place names

Suggested crawl target:

- 2 guide or list pages

Expected practical outcome:

- Enough information to choose a real weekend outing

### 5. Dinner Recommendation

Purpose:
Validate local decision support for same-day spending.

Search query:

```json
{
  "query": "上海 徐汇区 晚饭 推荐 人均100",
  "count": 8,
  "offset": 0
}
```

What to check:

- Whether geography and budget are reflected in results
- Whether results are practical rather than generic SEO
- Whether a user could actually choose where to eat tonight

Suggested crawl target:

- 1 ranking page and 1 guide page

Expected practical outcome:

- Enough information to pick a dinner option

### 6. Train / Transit Planning

Purpose:
Validate travel-related practical information lookup.

Search query:

```json
{
  "query": "上海到杭州 高铁 2026-05-02 最晚班次",
  "count": 8,
  "offset": 0
}
```

What to check:

- Whether results are relevant to same-day rail planning
- Whether official or credible travel sources appear
- Whether a user could judge if late travel is still possible

Suggested crawl target:

- Best transit page

Expected practical outcome:

- Enough information to support a basic travel decision

### 7. Family / Kid-friendly Outing

Purpose:
Validate family-oriented scenario handling.

Search query:

```json
{
  "query": "上海 适合带5岁孩子玩的地方",
  "count": 8,
  "offset": 0
}
```

What to check:

- Whether results are age/scenario appropriate
- Whether content is parent-useful rather than generic tourism
- Whether indoor/outdoor options are distinguishable

Suggested crawl target:

- Top 2 family guide results

Expected practical outcome:

- Enough information for a parent to shortlist options

### 8. Shopping Research

Purpose:
Validate product research and consumer comparison behavior.

Search query:

```json
{
  "query": "扫地机器人 推荐 2026 真实测评",
  "count": 8,
  "offset": 0
}
```

What to check:

- Whether results look like real evaluations rather than pure ads
- Whether multiple sources appear
- Whether a buyer could narrow choices after reading them

Suggested crawl target:

- Top 1 to 2 review pages

Expected practical outcome:

- Enough information to support a buying decision

## Stretch Cases

These are useful if the first 8 are green and you want to probe edge behavior.

### 9. Relative Time Wording

```json
{
  "query": "今天 上海 新闻",
  "count": 5,
  "offset": 0
}
```

Check whether relative-time phrasing performs worse than explicit dates.

### 10. Long Natural Language Query

```json
{
  "query": "我这周末在上海，预算500元，两个人，不想去太远，适合下午到晚上玩的地方有哪些",
  "count": 8,
  "offset": 0
}
```

Check whether quality collapses for realistic conversational phrasing.

### 11. Pagination Stability

Run both:

```json
{
  "query": "OpenAI 最新 新闻 2026-05-02",
  "count": 5,
  "offset": 0
}
```

```json
{
  "query": "OpenAI 最新 新闻 2026-05-02",
  "count": 5,
  "offset": 5
}
```

Check for:

- duplicate results
- sharp quality drop after pagination

## Suggested Result Template

Use this when recording outcomes:

```md
### Case N
- Query:
- Search pass/fail:
- Crawl pass/fail:
- Relevance:
- Freshness:
- Notes:
- Verdict: PASS / PARTIAL / FAIL
```

## Recommended First Batch

If you only want a compact smoke pass, run these first:

1. `上海 2026-05-02 天气 适合出门吗`
2. `2026-05-02 今日热点新闻 中国`
3. `OpenAI 最新 新闻 2026-05-02`
4. `上海 周末 去哪里玩 适合情侣 2026-05`
5. `上海 徐汇区 晚饭 推荐 人均100`
6. `上海到杭州 高铁 2026-05-02 最晚班次`
7. `上海 适合带5岁孩子玩的地方`
8. `扫地机器人 推荐 2026 真实测评`
