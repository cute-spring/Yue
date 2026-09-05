import type { YueChartSpec, ChartPrimitive } from './chartSpec';

export type YueChartThemeMode = 'light' | 'dark';

type EChartsOption = Record<string, unknown>;

const SERIES_PALETTE = ['#0f766e', '#2563eb', '#dc2626', '#7c3aed', '#ca8a04', '#0891b2', '#be185d', '#16a34a'];

const getThemeColors = (mode: YueChartThemeMode) =>
  mode === 'dark'
    ? {
        background: '#0d1117',
        text: '#e5e7eb',
        muted: '#9ca3af',
        axis: '#374151',
        split: '#1f2937',
      }
    : {
        background: '#ffffff',
        text: '#111827',
        muted: '#6b7280',
        axis: '#d1d5db',
        split: '#e5e7eb',
      };

const fieldLabel = (field: { field: string; label?: string; unit?: string }): string => {
  const label = field.label || field.field;
  return field.unit ? `${label} (${field.unit})` : label;
};

const primitiveToDisplay = (value: ChartPrimitive): string | number | null => {
  if (typeof value === 'boolean') return value ? 'true' : 'false';
  return value;
};

const sortedData = (spec: YueChartSpec) => {
  const rows = spec.data.map((row) => ({ ...row }));
  const sort = spec.presentation?.sort;
  if (!sort) return rows;
  return rows.sort((a, b) => {
    const left = a[sort.field];
    const right = b[sort.field];
    const direction = sort.order === 'asc' ? 1 : -1;
    if (typeof left === 'number' && typeof right === 'number') return (left - right) * direction;
    return String(left ?? '').localeCompare(String(right ?? '')) * direction;
  });
};

const makeDataset = (spec: YueChartSpec) => {
  const rows = sortedData(spec);
  const fields = Array.from(rows.reduce<Set<string>>((acc, row) => {
    Object.keys(row).forEach((field) => acc.add(field));
    return acc;
  }, new Set()));
  return {
    dimensions: fields,
    source: rows.map((row) => {
      const normalized: Record<string, string | number | null> = {};
      fields.forEach((field) => {
        normalized[field] = primitiveToDisplay(row[field]);
      });
      return normalized;
    }),
  };
};

const baseOption = (spec: YueChartSpec, mode: YueChartThemeMode): EChartsOption => {
  const colors = getThemeColors(mode);
  return {
    backgroundColor: colors.background,
    color: SERIES_PALETTE,
    title: {
      show: Boolean(spec.title || spec.subtitle),
      text: spec.title || '',
      subtext: spec.subtitle || '',
      left: 12,
      top: 10,
      textStyle: { color: colors.text, fontSize: 15, fontWeight: 700 },
      subtextStyle: { color: colors.muted, fontSize: 12 },
    },
    tooltip: {
      trigger: spec.chartType === 'pie' ? 'item' : 'axis',
      confine: true,
    },
    legend: {
      show: spec.presentation?.showLegend ?? ['pie', 'stacked-bar', 'multi-line'].includes(spec.chartType),
      bottom: 6,
      textStyle: { color: colors.muted },
    },
    grid: {
      left: 48,
      right: 24,
      top: spec.title || spec.subtitle ? 70 : 28,
      bottom: 48,
      containLabel: true,
    },
    dataset: makeDataset(spec),
    ...(spec.presentation?.showDataZoom && spec.chartType !== 'pie'
      ? {
          dataZoom: [
            { type: 'inside', throttle: 50 },
            { type: 'slider', height: 18, bottom: 28 },
          ],
        }
      : {}),
  };
};

const axisStyle = (mode: YueChartThemeMode) => {
  const colors = getThemeColors(mode);
  return {
    axisLine: { lineStyle: { color: colors.axis } },
    axisTick: { lineStyle: { color: colors.axis } },
    axisLabel: { color: colors.muted },
    splitLine: { lineStyle: { color: colors.split } },
    nameTextStyle: { color: colors.muted },
  };
};

const cartesianOption = (
  spec: YueChartSpec,
  mode: YueChartThemeMode,
  series: unknown[],
): EChartsOption => {
  const x = spec.encoding.x;
  const y = spec.encoding.y;
  return {
    ...baseOption(spec, mode),
    xAxis: {
      type: x?.type === 'time' ? 'time' : x?.type === 'number' ? 'value' : 'category',
      name: x ? fieldLabel(x) : undefined,
      ...axisStyle(mode),
    },
    yAxis: {
      type: y?.type === 'category' ? 'category' : 'value',
      name: y ? fieldLabel(y) : undefined,
      ...axisStyle(mode),
    },
    series,
  };
};

export function compileYueChartOption(spec: YueChartSpec, mode: YueChartThemeMode = 'light'): EChartsOption {
  if (spec.chartType === 'pie') {
    const category = spec.encoding.category;
    const value = spec.encoding.value;
    return {
      ...baseOption(spec, mode),
      series: [
        {
          type: 'pie',
          radius: ['38%', '68%'],
          center: ['50%', '52%'],
          encode: { itemName: category?.field, value: value?.field, tooltip: value?.field },
          name: value ? fieldLabel(value) : undefined,
          avoidLabelOverlap: true,
        },
      ],
    };
  }

  if (spec.chartType === 'stacked-bar') {
    return cartesianOption(
      spec,
      mode,
      (spec.encoding.series || []).map((series) => ({
        type: 'bar',
        name: series.label || series.field,
        stack: 'total',
        encode: { x: spec.encoding.x?.field, y: series.field },
      })),
    );
  }

  if (spec.chartType === 'multi-line') {
    return cartesianOption(
      spec,
      mode,
      (spec.encoding.series || []).map((series) => ({
        type: 'line',
        name: series.label || series.field,
        smooth: true,
        symbolSize: 6,
        encode: { x: spec.encoding.x?.field, y: series.field },
      })),
    );
  }

  const y = spec.encoding.y;
  const commonEncode = { x: spec.encoding.x?.field, y: y?.field };
  if (spec.chartType === 'bar') {
    return cartesianOption(spec, mode, [{ type: 'bar', name: y ? fieldLabel(y) : undefined, encode: commonEncode }]);
  }
  if (spec.chartType === 'scatter') {
    return cartesianOption(spec, mode, [{ type: 'scatter', name: y ? fieldLabel(y) : undefined, symbolSize: 8, encode: commonEncode }]);
  }
  return cartesianOption(spec, mode, [
    {
      type: 'line',
      name: y ? fieldLabel(y) : undefined,
      smooth: true,
      symbolSize: 6,
      areaStyle: spec.chartType === 'area' ? {} : undefined,
      encode: commonEncode,
    },
  ]);
}
