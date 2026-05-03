# Amap MCP Real-World Test Report

Date:
- 2026-05-02

Service under test:
- `amap-maps`
- transport: `streamable_http`
- url: `https://mcp.amap.com/mcp?key=112e860beca64ae06c0745af69bd7896`

Server identity observed at runtime:
- `server_name = amap-sse-server`
- `version = 1.0.0`

Tools exercised:
- `maps_weather`
- `maps_text_search`
- `maps_geo`
- `maps_regeocode`
- `maps_distance`
- `maps_direction_walking`
- `maps_direction_driving`
- `maps_direction_transit_integrated`

## Overall Verdict

Current status:
- **Connectivity:** PASS
- **Tool discovery:** PASS
- **Structured API responses:** PASS
- **Real-world usefulness:** PASS
- **Operational stability in tested scenarios:** PASS

Summary:
- Yue connected successfully to the remote Amap MCP service.
- Tool discovery succeeded.
- All tested scenarios returned structured and practically useful results.
- Compared with the earlier Bing CN MCP evaluation, this service is substantially more reliable for real daily-life use cases because its outputs are structured and domain-specific rather than open-web search results.

## Connection Validation

Observed during testing:
- `connected = true`
- `transport = streamable_http`
- `last_error = null`

This confirms that the Yue-side transport integration and the remote Amap MCP endpoint are both working.

## Test Cases

### 1. Shanghai Weather

- Tool: `maps_weather`
- Input:

```json
{
  "city": "上海"
}
```

- Result: PASS
- Returned:
  - multi-day weather forecast
  - `2026-05-02` daytime weather: `小雨`
  - `2026-05-02` nighttime weather: `中雨`
  - `2026-05-02` temperatures: `24 / 17`
- Practical usefulness:
  - strong
  - directly usable for same-day planning

### 2. POI Search: Coffee Shops in Shanghai

- Tool: `maps_text_search`
- Input:

```json
{
  "keywords": "咖啡店",
  "city": "上海",
  "citylimit": true
}
```

- Result: PASS
- Returned:
  - multiple concrete POIs
  - examples included:
    - `Manner Coffee(国客滨江店)`
    - `星巴克臻选(上海烘焙工坊)`
    - `DünDun&Co.`
    - `铁手咖啡制造局`
- Practical usefulness:
  - strong
  - supports real local place discovery

### 3. Geocoding

- Tool: `maps_geo`
- Input:

```json
{
  "address": "上海迪士尼乐园",
  "city": "上海"
}
```

- Result: PASS
- Returned:
  - structured location record
  - coordinates: `121.660294,31.143212`
  - district: `浦东新区`
- Practical usefulness:
  - strong
  - directly usable for downstream routing and map workflows

### 4. Reverse Geocoding

- Tool: `maps_regeocode`
- Input:

```json
{
  "location": "121.506377,31.245105"
}
```

- Result: PASS
- Returned:
  - country: `中国`
  - province: `上海市`
  - district: `浦东新区`
- Practical usefulness:
  - good
  - useful for region identification and context filling

### 5. Distance Measurement

- Tool: `maps_distance`
- Input:

```json
{
  "origins": "121.667959,31.149712",
  "destination": "121.490317,31.241701",
  "type": "1"
}
```

- Result: PASS
- Returned:
  - distance: `33247`
  - duration: `3012`
- Practical usefulness:
  - strong
  - useful for direct travel estimation

### 6. Walking Route

- Tool: `maps_direction_walking`
- Input:

```json
{
  "origin": "121.473667,31.230525",
  "destination": "121.490317,31.241701"
}
```

- Result: PASS
- Returned:
  - route summary
  - total walking distance
  - total walking duration
  - step-by-step instructions
- Practical usefulness:
  - strong
  - directly suitable for assistant-style navigation support

### 7. Driving Route

- Tool: `maps_direction_driving`
- Input:

```json
{
  "origin": "121.327527,31.200274",
  "destination": "121.799805,31.151826"
}
```

- Result: PASS
- Returned:
  - route summary
  - total driving distance
  - total driving duration
  - detailed step instructions
- Practical usefulness:
  - strong
  - suitable for trip planning and ETA-style reasoning

### 8. Public Transit Route

- Tool: `maps_direction_transit_integrated`
- Input:

```json
{
  "origin": "121.462554,31.253573",
  "destination": "121.667959,31.149712",
  "city": "上海",
  "cityd": "上海"
}
```

- Result: PASS
- Returned:
  - total route distance
  - total duration
  - walking segments
  - metro segments
  - transfer structure
- Example:
  - route included metro line 8 and metro line 11
- Practical usefulness:
  - strong
  - good fit for real transit guidance scenarios

## Product Assessment

### What this MCP is good at

- weather lookup
- structured POI search
- geocoding / reverse geocoding
- travel distance estimation
- walking / driving / transit route planning

### Why it performed better than Bing CN MCP

This service performed better because:

- it is domain-specific
- responses are structured rather than free-form web snippets
- there is no dependence on arbitrary search ranking quality
- the output is already shaped for downstream reasoning by the assistant

## Practical Recommendation

This MCP is suitable for:

- real user-facing location and travel flows
- structured planning workflows
- assistant features involving weather, routes, or place lookup

This MCP appears much more production-viable than the previously tested Bing CN MCP for daily-use scenarios.

## Final Verdict Table

| Case | Scenario | Verdict |
|---|---|---|
| 1 | Shanghai weather | PASS |
| 2 | Coffee shop POI search | PASS |
| 3 | Geocoding Shanghai Disney | PASS |
| 4 | Reverse geocoding Pudong coordinate | PASS |
| 5 | Distance measurement | PASS |
| 6 | Walking route planning | PASS |
| 7 | Driving route planning | PASS |
| 8 | Public transit route planning | PASS |

## Final Conclusion

If the question is:

- “Does Yue connect to Amap MCP successfully?” -> **Yes**
- “Do the tools return useful real-world results?” -> **Yes**
- “Is this suitable for realistic map / weather / routing scenarios?” -> **Yes**

This is currently one of the strongest remote MCP integrations tested in this session.
