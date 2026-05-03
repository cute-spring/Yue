# Bing CN MCP Real-World Test Report

Date:
- 2026-05-02

Service under test:
- `bing-cn-mcp-server`
- transport: `streamable_http`
- url: `https://mcp.api-inference.modelscope.net/6ab3a144b1994a/mcp`

Tools exercised:
- `bing_search`
- `crawl_webpage`

Execution path:
- Real runtime through Yue MCP manager
- Real remote calls to the live ModelScope endpoint

## Overall Verdict

Current status:
- **Connectivity:** PASS
- **Tool discovery:** PASS
- **Basic query execution:** PASS
- **Real-world relevance quality:** FAIL
- **Search -> crawl practical workflow:** PARTIAL

Summary:
- The service is technically reachable and callable.
- The remote endpoint returns results and exposes tools correctly.
- However, the search quality for realistic Chinese consumer queries is currently weak in this environment.
- Several very different Shanghai lifestyle queries collapsed into nearly identical Zhihu-heavy results.
- Crawl often returns a blacklist error for the top result, which limits practical usefulness even when search succeeds.
- One time-sensitive news query timed out entirely during testing.

## Environment Notes

Observed during testing:
- Yue connected to the service successfully.
- Yue discovered 2 tools from the remote server:
  - `bing_search`
  - `crawl_webpage`
- Remote server identity reported earlier in live validation:
  - `server_name = bing-cn-search`
  - `version = 1.9.4`

## Case Results

### Case 1
- Query: `上海 2026-05-02 天气 适合出门吗`
- Search result count: 10
- Search verdict: FAIL
- Crawl verdict: PARTIAL
- Relevance:
  - Top results were general Shanghai Zhihu/travel pages.
  - Results did not reflect weather intent.
- Freshness:
  - Top result was from 2023.
- Crawl result:
  - Top page crawl returned blacklist error.
- Notes:
  - This is a strong miss for a realistic same-day weather query.
- Verdict: FAIL

### Case 2
- Query: `2026-05-02 今日热点新闻 中国`
- Search verdict: FAIL
- Crawl verdict: NOT RUN
- Relevance:
  - Search request timed out before producing results.
- Freshness:
  - Not assessable.
- Notes:
  - A same-day headline query is a core real-world scenario, so timeout is meaningful.
- Verdict: FAIL

### Case 3
- Query: `OpenAI 最新 新闻 2026-05-02`
- Search result count: 10
- Search verdict: PARTIAL
- Crawl verdict: PARTIAL
- Relevance:
  - Search returned OpenAI-related content.
  - Top results were still Zhihu-heavy and mixed “news” with general discussion/use questions.
- Freshness:
  - Top visible result referenced 2026-04-03, which is reasonably recent.
  - Other results were older or less clearly “latest news”.
- Crawl result:
  - Top page crawl returned blacklist error.
- Notes:
  - Better than the Shanghai lifestyle cases, but still not strong enough for high-confidence news monitoring.
- Verdict: PARTIAL

### Case 4
- Query: `上海 周末 去哪里玩 适合情侣 2026-05`
- Search result count: 10
- Search verdict: FAIL
- Crawl verdict: PARTIAL
- Relevance:
  - Top results again collapsed to generic Shanghai Zhihu/travel content.
  - Poor scenario matching for “couple weekend outing”.
- Freshness:
  - Top result was from 2023.
- Crawl result:
  - Top page crawl returned blacklist error.
- Notes:
  - This query should have produced recommendation-style guides, but did not.
- Verdict: FAIL

### Case 5
- Query: `上海 徐汇区 晚饭 推荐 人均100`
- Search result count: 10
- Search verdict: FAIL
- Crawl verdict: PARTIAL
- Relevance:
  - Top results were again generic Shanghai Zhihu pages, not dinner recommendations.
  - Geography and budget intent were not reflected.
- Freshness:
  - Top result was from 2023.
- Crawl result:
  - Top page crawl returned blacklist error.
- Notes:
  - This is a practical consumer decision query, and the returned ranking was not useful.
- Verdict: FAIL

## Key Findings

### 1. Technical path is working

What passed:
- Yue can connect to the remote MCP endpoint.
- Yue can discover tools.
- Yue can execute `bing_search`.
- Yue can execute `crawl_webpage`.

This means the transport integration is working end to end.

### 2. Search quality is not yet good enough for realistic local Chinese queries

Observed pattern:
- Multiple distinct Shanghai queries returned almost the same top Zhihu-oriented results.
- Query intent was not reflected well in ranking.
- Weather, dining, and weekend-travel scenarios all looked overly generic.

### 3. Crawl path works, but top-result usefulness is often blocked

Observed pattern:
- The tool returned structured crawl responses.
- But top returned pages were often blacklisted by the crawler.

Practical effect:
- Even when search returns something, the second step may fail to provide usable page content.

### 4. Time-sensitive queries are not fully reliable

Observed pattern:
- Same-day China news query timed out.
- News-style use cases may need retries or fallback strategies.

## Practical Assessment

If the goal is to test Yue’s transport and live remote-tool plumbing:
- **PASS**

If the goal is to rely on this service for realistic consumer-facing Chinese search workflows:
- **NOT YET RELIABLE**

Best current fit:
- lightweight exploratory lookup
- technical integration validation
- rough search assistance

Poor current fit:
- weather-style daily decisions
- local recommendation queries
- dining/nearby decision support
- high-confidence “today’s news” use cases

## Recommendations

### Product / integration

- Keep this server as a live transport validation target.
- Do not treat it yet as a high-confidence production recommendation/search source for local lifestyle scenarios.

### Testing

Next suggested follow-up cases:
- retry the failed headline query with a smaller `count`
- run broader news/media queries that are less local
- test whether English or mixed Chinese-English AI queries rank better
- probe whether lower `count` improves relevance or stability

### Reporting

For future runs, record:
- whether results are duplicated across unrelated queries
- how often top pages are blocked by crawl blacklist
- whether retrying improves time-sensitive queries

## Final Verdict Table

| Case | Scenario | Verdict |
|---|---|---|
| 1 | Today weather | FAIL |
| 2 | Today headlines | FAIL |
| 3 | OpenAI latest news | PARTIAL |
| 4 | Weekend outing | FAIL |
| 5 | Dinner recommendation | FAIL |

