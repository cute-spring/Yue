# Bing CN MCP Real-World Test Report Batch 2

Date:
- 2026-05-02

Service under test:
- `bing-cn-mcp-server`
- transport: `streamable_http`
- url: `https://mcp.api-inference.modelscope.net/6ab3a144b1994a/mcp`

Focus of this batch:
- news
- technology
- general information lookup
- shopping research
- practical troubleshooting

## Overall Verdict

Current batch status:
- **International / same-day news:** FAIL
- **General technology lookup:** PARTIAL
- **Developer / AI tooling topics:** PASS
- **Shopping / recommendation quality:** FAIL
- **Practical troubleshooting:** FAIL
- **Remote stability under repeated calls:** PARTIAL

Summary:
- This service performs noticeably better on broad developer/AI ecosystem topics than on local lifestyle topics from batch 1.
- However, same-day news queries still timed out.
- Product recommendation and practical troubleshooting queries were still poorly matched.
- The crawl path sometimes succeeded on non-blacklisted pages, but remote response truncation still appeared during the run.

## Case Results

### Case 6
- Query: `2026-05-02 国际新闻 头条`
- Search verdict: FAIL
- Crawl verdict: NOT RUN
- Notes:
  - Search timed out.
- Verdict: FAIL

### Case 7
- Query: `2026-05-02 科技新闻 AI`
- Search verdict: FAIL
- Crawl verdict: NOT RUN
- Notes:
  - Search timed out.
- Verdict: FAIL

### Case 8
- Query: `Claude GPT Gemini 最新 对比`
- Search result count: 10
- Search verdict: PARTIAL to PASS
- Crawl verdict: PASS
- Relevance:
  - Returned strongly tech-oriented results.
  - Top result was a GitHub guide related to Claude Code rather than a clean GPT/Claude/Gemini comparison article.
  - Still much more on-topic than the local consumer cases.
- Freshness:
  - Top visible result referenced `2026-01-08`.
- Crawl result:
  - Crawl succeeded on the GitHub page.
  - Returned substantial readable content.
- Practical usefulness:
  - Useful for AI/dev ecosystem exploration.
  - Less ideal if the exact need is a structured model comparison.
- Verdict: PASS

### Case 9
- Query: `扫地机器人 推荐 2026 真实测评`
- Search result count: 10
- Search verdict: FAIL
- Crawl verdict: PASS technically, FAIL practically
- Relevance:
  - Top result was relevant.
  - But the second crawled non-Zhihu candidate was completely irrelevant: a Baidu Jingyan page about how to sweep the floor manually.
- Freshness:
  - Top visible relevant result referenced `2026-04-04`.
- Crawl result:
  - Crawl succeeded on the Baidu page.
  - But the content was not useful for robot-vacuum purchase research.
- Practical usefulness:
  - Weak.
  - Ranking quality is not reliable enough for shopping research.
- Verdict: FAIL

### Case 10
- Query: `空调不制冷 原因 怎么判断`
- Search result count: 10
- Search verdict: FAIL
- Crawl verdict: PARTIAL
- Relevance:
  - Top results were about buying air conditioners, not diagnosing why one is not cooling.
  - Intent understanding was poor.
- Freshness:
  - Returned recent pages, but they were the wrong kind of pages.
- Crawl result:
  - Top result was blacklisted.
- Practical usefulness:
  - Not sufficient for troubleshooting.
- Verdict: FAIL

## Cross-Batch Interpretation

Combining batch 1 and batch 2:

### What works

- Yue transport integration is working.
- Remote MCP handshake, tool listing, and live calls are working.
- Broad AI / developer information discovery can work reasonably.
- Crawl can return useful content when the selected result is not blacklisted and the remote response completes normally.

### What does not work well

- Same-day news retrieval reliability
- Local lifestyle relevance
- Consumer recommendation quality
- Practical troubleshooting intent matching
- Stable search -> crawl workflow on blacklisted or brittle result sources

### Strong pattern observed

The service appears to be:
- better at broad web discovery around AI / developer / technical topics
- worse at high-intent practical consumer queries
- weaker on freshness-sensitive news queries than expected

## Stability Findings

Observed during this batch:
- Multiple remote response parsing failures caused by truncated HTTP response bodies
- Timeouts on some news-style queries

Implication:
- Even when query relevance is acceptable, the remote service may still be operationally unstable under repeated realistic calls

## Final Product Assessment

Best current fit:
- remote MCP transport validation
- AI/dev-topic exploration
- lightweight web discovery

Poor current fit:
- weather
- local dining / travel / leisure decisions
- shopping recommendation research
- troubleshooting / diagnosis
- same-day headline/news dependence

## Final Verdict Table

| Case | Scenario | Verdict |
|---|---|---|
| 6 | International headlines | FAIL |
| 7 | AI tech news today | FAIL |
| 8 | Claude/GPT/Gemini comparison | PASS |
| 9 | Robot vacuum shopping research | FAIL |
| 10 | Air conditioner troubleshooting | FAIL |

## Combined High-Level Conclusion

If the question is:
- “Does the MCP integration work end to end?” -> **Yes**
- “Can this server be trusted for realistic Chinese daily-life search workflows?” -> **No, not reliably**
- “Is it better suited for AI/developer topic lookup than local consumer scenarios?” -> **Yes, clearly**

