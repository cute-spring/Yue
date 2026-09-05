import { describe, expect, it } from 'vitest';
import { CHART_SPEC_LIMITS, parseYueChartSpec, validateYueChartSpec } from './chartSpec';

const baseBarSpec = {
  version: 1,
  kind: 'chart',
  chartType: 'bar',
  title: 'Revenue by Region',
  data: [
    { region: 'APAC', revenue: 120 },
    { region: 'EMEA', revenue: 90 },
  ],
  encoding: {
    x: { field: 'region', type: 'category', label: 'Region' },
    y: { field: 'revenue', type: 'number', label: 'Revenue' },
  },
};

describe('chartSpec', () => {
  it('accepts a valid bar chart spec', () => {
    const result = validateYueChartSpec(baseBarSpec);
    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.spec.chartType).toBe('bar');
      expect(result.spec.encoding.x?.field).toBe('region');
    }
  });

  it('accepts Chinese field names and labels', () => {
    const result = validateYueChartSpec({
      version: 1,
      kind: 'chart',
      chartType: 'line',
      title: '月度收入',
      data: [
        { 月份: '一月', 收入: 120 },
        { 月份: '二月', 收入: 140 },
      ],
      encoding: {
        x: { field: '月份', type: 'category', label: '月份' },
        y: { field: '收入', type: 'number', label: '收入' },
      },
    });
    expect(result.ok).toBe(true);
    if (result.ok) expect(result.spec.encoding.y?.field).toBe('收入');
  });

  it('enforces chart-type-specific encoding requirements', () => {
    const result = validateYueChartSpec({
      ...baseBarSpec,
      chartType: 'pie',
      encoding: baseBarSpec.encoding,
    });
    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.error.code).toBe('invalid_encoding');
      expect(result.error.path).toBe('$.encoding.category');
    }
  });

  it('rejects missing referenced fields', () => {
    const result = validateYueChartSpec({
      ...baseBarSpec,
      encoding: {
        x: { field: 'region', type: 'category' },
        y: { field: 'profit', type: 'number' },
      },
    });
    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.error.code).toBe('invalid_reference');
  });

  it('rejects unsafe raw ECharts option fields', () => {
    const result = validateYueChartSpec({
      ...baseBarSpec,
      echartsOption: { tooltip: { formatter: 'function () { return 1; }' } },
    });
    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.error.code).toBe('unsafe_field');
  });

  it('does not reject harmless display text containing suspicious words', () => {
    const result = validateYueChartSpec({
      ...baseBarSpec,
      title: 'The formatter function concept over time',
    });
    expect(result.ok).toBe(true);
  });

  it('rejects oversized datasets', () => {
    const result = validateYueChartSpec({
      ...baseBarSpec,
      data: Array.from({ length: CHART_SPEC_LIMITS.maxRows + 1 }, (_, index) => ({
        region: `R${index}`,
        revenue: index,
      })),
    });
    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.error.code).toBe('dataset_too_large');
  });

  it('parses JSON before validation', () => {
    const result = parseYueChartSpec(JSON.stringify(baseBarSpec));
    expect(result.ok).toBe(true);
  });

  it('reports invalid JSON clearly', () => {
    const result = parseYueChartSpec('{');
    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.error.code).toBe('invalid_json');
  });
});
