import { describe, expect, it } from 'vitest';
import { compileYueChartOption } from './chartCompiler';
import type { YueChartSpec } from './chartSpec';

describe('chartCompiler', () => {
  it('compiles a bar chart to dataset-backed ECharts options', () => {
    const spec: YueChartSpec = {
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

    const option = compileYueChartOption(spec);

    expect(option.dataset).toMatchObject({
      dimensions: ['region', 'revenue'],
      source: [
        { region: 'APAC', revenue: 120 },
        { region: 'EMEA', revenue: 90 },
      ],
    });
    expect(option.series).toMatchObject([{ type: 'bar', encode: { x: 'region', y: 'revenue' } }]);
    expect(JSON.stringify(option)).not.toContain('function');
  });

  it('compiles pie charts with category and value encodings', () => {
    const spec: YueChartSpec = {
      version: 1,
      kind: 'chart',
      chartType: 'pie',
      data: [
        { category: 'Free', users: 1200 },
        { category: 'Paid', users: 300 },
      ],
      encoding: {
        category: { field: 'category', type: 'category' },
        value: { field: 'users', type: 'number', label: 'Users' },
      },
    };

    const option = compileYueChartOption(spec, 'dark');

    expect(option.backgroundColor).toBe('#0d1117');
    expect(option.series).toMatchObject([
      {
        type: 'pie',
        encode: { itemName: 'category', value: 'users', tooltip: 'users' },
      },
    ]);
  });

  it('compiles multi-line series in order', () => {
    const spec: YueChartSpec = {
      version: 1,
      kind: 'chart',
      chartType: 'multi-line',
      data: [
        { month: 'Jan', free: 1200, paid: 300 },
        { month: 'Feb', free: 1400, paid: 380 },
      ],
      encoding: {
        x: { field: 'month', type: 'category' },
        series: [
          { field: 'free', label: 'Free' },
          { field: 'paid', label: 'Paid' },
        ],
      },
    };

    const option = compileYueChartOption(spec);

    expect(option.series).toMatchObject([
      { type: 'line', name: 'Free', encode: { x: 'month', y: 'free' } },
      { type: 'line', name: 'Paid', encode: { x: 'month', y: 'paid' } },
    ]);
  });
});
