export const CHART_SPEC_LIMITS = {
  maxRows: 500,
  maxColumns: 30,
  maxSeries: 12,
  maxTitleLength: 120,
  maxSubtitleLength: 200,
  maxLabelLength: 80,
  maxFieldNameLength: 80,
  maxCellStringLength: 500,
  maxSerializedBytes: 256 * 1024,
} as const;

export const YUE_CHART_BLOCK_LANGUAGE = 'yue-chart';

export type YueChartType =
  | 'bar'
  | 'line'
  | 'area'
  | 'pie'
  | 'scatter'
  | 'stacked-bar'
  | 'multi-line';

export type ChartFieldType = 'category' | 'number' | 'time';
export type ChartPrimitive = string | number | boolean | null;
export type ChartDataRow = Record<string, ChartPrimitive>;

export type ChartFieldEncoding = {
  field: string;
  type: ChartFieldType;
  label?: string;
  unit?: string;
};

export type ChartSeriesEncoding = {
  field: string;
  label?: string;
  unit?: string;
};

export type YueChartSpec = {
  version: 1;
  kind: 'chart';
  chartType: YueChartType;
  title?: string;
  subtitle?: string;
  data: ChartDataRow[];
  encoding: {
    x?: ChartFieldEncoding;
    y?: ChartFieldEncoding;
    series?: ChartSeriesEncoding[];
    category?: ChartFieldEncoding;
    value?: ChartFieldEncoding;
    color?: ChartFieldEncoding;
  };
  presentation?: {
    sort?: {
      field: string;
      order: 'asc' | 'desc';
    };
    showLegend?: boolean;
    showDataZoom?: boolean;
    valueFormat?: 'plain' | 'currency' | 'percent' | 'compact';
  };
};

type ChartPresentation = NonNullable<YueChartSpec['presentation']>;

export type ChartSpecErrorCode =
  | 'invalid_json'
  | 'invalid_shape'
  | 'invalid_version'
  | 'invalid_kind'
  | 'invalid_chart_type'
  | 'invalid_encoding'
  | 'invalid_data'
  | 'invalid_reference'
  | 'invalid_type'
  | 'payload_too_large'
  | 'dataset_too_large'
  | 'label_too_long'
  | 'unsafe_field';

export type ChartSpecError = {
  code: ChartSpecErrorCode;
  message: string;
  path?: string;
};

export type ChartSpecValidationResult =
  | { ok: true; spec: YueChartSpec }
  | { ok: false; error: ChartSpecError };

const ALLOWED_CHART_TYPES = new Set<YueChartType>([
  'bar',
  'line',
  'area',
  'pie',
  'scatter',
  'stacked-bar',
  'multi-line',
]);

const ALLOWED_FIELD_TYPES = new Set<ChartFieldType>(['category', 'number', 'time']);

const FORBIDDEN_FIELD_NAMES = new Set([
  'echartsoption',
  'rawoption',
  'option',
  'formatter',
  'tooltiphtml',
  'html',
  'unsafehtml',
  'dangerouslysetinnerhtml',
]);

const byteLength = (value: string): number => new TextEncoder().encode(value).length;

const fail = (code: ChartSpecErrorCode, message: string, path?: string): ChartSpecValidationResult => ({
  ok: false,
  error: { code, message, path },
});

const isObject = (value: unknown): value is Record<string, unknown> =>
  typeof value === 'object' && value !== null && !Array.isArray(value);

const isPrimitive = (value: unknown): value is ChartPrimitive =>
  value === null || typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean';

const isForbiddenKey = (key: string): boolean => FORBIDDEN_FIELD_NAMES.has(key.replace(/[-_\s]/g, '').toLowerCase());

const findForbiddenField = (value: unknown, path = '$'): string | null => {
  if (Array.isArray(value)) {
    for (let index = 0; index < value.length; index += 1) {
      const found = findForbiddenField(value[index], `${path}[${index}]`);
      if (found) return found;
    }
    return null;
  }
  if (!isObject(value)) return null;
  for (const [key, child] of Object.entries(value)) {
    const childPath = `${path}.${key}`;
    if (isForbiddenKey(key)) return childPath;
    const found = findForbiddenField(child, childPath);
    if (found) return found;
  }
  return null;
};

const validateText = (
  value: unknown,
  path: string,
  maxLength: number,
  code: ChartSpecErrorCode = 'label_too_long',
): ChartSpecError | null => {
  if (value === undefined) return null;
  if (typeof value !== 'string') {
    return { code: 'invalid_shape', message: `${path} must be a string`, path };
  }
  if (value.length > maxLength) {
    return { code, message: `${path} exceeds ${maxLength} characters`, path };
  }
  return null;
};

const validateFieldEncoding = (
  value: unknown,
  path: string,
  allowedTypes: ChartFieldType[],
  fields: Set<string>,
): ChartFieldEncoding | ChartSpecError => {
  if (!isObject(value)) {
    return { code: 'invalid_encoding', message: `${path} must be an object`, path };
  }
  const field = value.field;
  const type = value.type;
  if (typeof field !== 'string' || !field) {
    return { code: 'invalid_encoding', message: `${path}.field is required`, path: `${path}.field` };
  }
  if (field.length > CHART_SPEC_LIMITS.maxFieldNameLength) {
    return {
      code: 'label_too_long',
      message: `${path}.field exceeds ${CHART_SPEC_LIMITS.maxFieldNameLength} characters`,
      path: `${path}.field`,
    };
  }
  if (!fields.has(field)) {
    return { code: 'invalid_reference', message: `${path}.field references missing data field "${field}"`, path: `${path}.field` };
  }
  if (typeof type !== 'string' || !ALLOWED_FIELD_TYPES.has(type as ChartFieldType)) {
    return { code: 'invalid_type', message: `${path}.type must be category, number, or time`, path: `${path}.type` };
  }
  if (!allowedTypes.includes(type as ChartFieldType)) {
    return {
      code: 'invalid_type',
      message: `${path}.type must be ${allowedTypes.join(' or ')}`,
      path: `${path}.type`,
    };
  }
  const labelError = validateText(value.label, `${path}.label`, CHART_SPEC_LIMITS.maxLabelLength);
  if (labelError) return labelError;
  const unitError = validateText(value.unit, `${path}.unit`, CHART_SPEC_LIMITS.maxLabelLength);
  if (unitError) return unitError;
  return {
    field,
    type: type as ChartFieldType,
    ...(typeof value.label === 'string' ? { label: value.label } : {}),
    ...(typeof value.unit === 'string' ? { unit: value.unit } : {}),
  };
};

const validateSeries = (
  value: unknown,
  fields: Set<string>,
): ChartSeriesEncoding[] | ChartSpecError => {
  if (!Array.isArray(value) || value.length === 0) {
    return { code: 'invalid_encoding', message: 'encoding.series must be a non-empty array', path: '$.encoding.series' };
  }
  if (value.length > CHART_SPEC_LIMITS.maxSeries) {
    return {
      code: 'dataset_too_large',
      message: `encoding.series exceeds ${CHART_SPEC_LIMITS.maxSeries} series`,
      path: '$.encoding.series',
    };
  }
  return value.map((entry, index) => {
    const path = `$.encoding.series[${index}]`;
    if (!isObject(entry)) {
      return { code: 'invalid_encoding', message: `${path} must be an object`, path } as ChartSpecError;
    }
    const field = entry.field;
    if (typeof field !== 'string' || !field) {
      return { code: 'invalid_encoding', message: `${path}.field is required`, path: `${path}.field` } as ChartSpecError;
    }
    if (field.length > CHART_SPEC_LIMITS.maxFieldNameLength) {
      return {
        code: 'label_too_long',
        message: `${path}.field exceeds ${CHART_SPEC_LIMITS.maxFieldNameLength} characters`,
        path: `${path}.field`,
      } as ChartSpecError;
    }
    if (!fields.has(field)) {
      return { code: 'invalid_reference', message: `${path}.field references missing data field "${field}"`, path: `${path}.field` } as ChartSpecError;
    }
    const labelError = validateText(entry.label, `${path}.label`, CHART_SPEC_LIMITS.maxLabelLength);
    if (labelError) return labelError;
    const unitError = validateText(entry.unit, `${path}.unit`, CHART_SPEC_LIMITS.maxLabelLength);
    if (unitError) return unitError;
    return {
      field,
      ...(typeof entry.label === 'string' ? { label: entry.label } : {}),
      ...(typeof entry.unit === 'string' ? { unit: entry.unit } : {}),
    } satisfies ChartSeriesEncoding;
  }).reduce<ChartSeriesEncoding[] | ChartSpecError>((acc, item) => {
    if (!Array.isArray(acc)) return acc;
    if ('code' in item) return item;
    return [...acc, item];
  }, []);
};

const validateData = (value: unknown): { rows: ChartDataRow[]; fields: Set<string> } | ChartSpecError => {
  if (!Array.isArray(value) || value.length === 0) {
    return { code: 'invalid_data', message: 'data must be a non-empty array', path: '$.data' };
  }
  if (value.length > CHART_SPEC_LIMITS.maxRows) {
    return { code: 'dataset_too_large', message: `data exceeds ${CHART_SPEC_LIMITS.maxRows} rows`, path: '$.data' };
  }

  const fields = new Set<string>();
  const rows: ChartDataRow[] = [];
  for (let index = 0; index < value.length; index += 1) {
    const row = value[index];
    const path = `$.data[${index}]`;
    if (!isObject(row)) {
      return { code: 'invalid_data', message: `${path} must be an object`, path };
    }
    const normalized: ChartDataRow = {};
    for (const [key, cell] of Object.entries(row)) {
      if (!key || key.length > CHART_SPEC_LIMITS.maxFieldNameLength) {
        return {
          code: 'label_too_long',
          message: `${path} contains an invalid or too-long field name`,
          path,
        };
      }
      if (!isPrimitive(cell)) {
        return { code: 'invalid_data', message: `${path}.${key} must be a primitive value`, path: `${path}.${key}` };
      }
      if (typeof cell === 'string' && cell.length > CHART_SPEC_LIMITS.maxCellStringLength) {
        return {
          code: 'label_too_long',
          message: `${path}.${key} exceeds ${CHART_SPEC_LIMITS.maxCellStringLength} characters`,
          path: `${path}.${key}`,
        };
      }
      fields.add(key);
      normalized[key] = cell;
    }
    rows.push(normalized);
  }
  if (fields.size > CHART_SPEC_LIMITS.maxColumns) {
    return { code: 'dataset_too_large', message: `data exceeds ${CHART_SPEC_LIMITS.maxColumns} columns`, path: '$.data' };
  }
  return { rows, fields };
};

const validatePresentation = (value: unknown, fields: Set<string>): YueChartSpec['presentation'] | ChartSpecError | undefined => {
  if (value === undefined) return undefined;
  if (!isObject(value)) {
    return { code: 'invalid_shape', message: 'presentation must be an object', path: '$.presentation' };
  }
  const result: ChartPresentation = {};
  if (value.sort !== undefined) {
    if (!isObject(value.sort)) {
      return { code: 'invalid_shape', message: 'presentation.sort must be an object', path: '$.presentation.sort' };
    }
    if (typeof value.sort.field !== 'string' || !fields.has(value.sort.field)) {
      return { code: 'invalid_reference', message: 'presentation.sort.field references a missing data field', path: '$.presentation.sort.field' };
    }
    if (value.sort.order !== 'asc' && value.sort.order !== 'desc') {
      return { code: 'invalid_shape', message: 'presentation.sort.order must be asc or desc', path: '$.presentation.sort.order' };
    }
    result.sort = { field: value.sort.field, order: value.sort.order };
  }
  if (value.showLegend !== undefined) {
    if (typeof value.showLegend !== 'boolean') {
      return { code: 'invalid_shape', message: 'presentation.showLegend must be a boolean', path: '$.presentation.showLegend' };
    }
    result.showLegend = value.showLegend;
  }
  if (value.showDataZoom !== undefined) {
    if (typeof value.showDataZoom !== 'boolean') {
      return { code: 'invalid_shape', message: 'presentation.showDataZoom must be a boolean', path: '$.presentation.showDataZoom' };
    }
    result.showDataZoom = value.showDataZoom;
  }
  if (value.valueFormat !== undefined) {
    if (!['plain', 'currency', 'percent', 'compact'].includes(String(value.valueFormat))) {
      return { code: 'invalid_shape', message: 'presentation.valueFormat is unsupported', path: '$.presentation.valueFormat' };
    }
    result.valueFormat = value.valueFormat as ChartPresentation['valueFormat'];
  }
  return result;
};

export function validateYueChartSpec(value: unknown): ChartSpecValidationResult {
  let serialized = '';
  try {
    serialized = JSON.stringify(value);
  } catch {
    return fail('invalid_shape', 'Chart spec must be JSON serializable');
  }
  if (byteLength(serialized) > CHART_SPEC_LIMITS.maxSerializedBytes) {
    return fail('payload_too_large', `Chart spec exceeds ${CHART_SPEC_LIMITS.maxSerializedBytes} bytes`);
  }

  const forbiddenPath = findForbiddenField(value);
  if (forbiddenPath) {
    return fail('unsafe_field', `Chart spec contains forbidden field at ${forbiddenPath}`, forbiddenPath);
  }

  if (!isObject(value)) return fail('invalid_shape', 'Chart spec must be an object', '$');
  if (value.version !== 1) return fail('invalid_version', 'Chart spec version must be 1', '$.version');
  if (value.kind !== 'chart') return fail('invalid_kind', 'Chart spec kind must be chart', '$.kind');
  if (typeof value.chartType !== 'string' || !ALLOWED_CHART_TYPES.has(value.chartType as YueChartType)) {
    return fail('invalid_chart_type', 'Chart spec chartType is unsupported', '$.chartType');
  }

  const titleError = validateText(value.title, '$.title', CHART_SPEC_LIMITS.maxTitleLength);
  if (titleError) return { ok: false, error: titleError };
  const subtitleError = validateText(value.subtitle, '$.subtitle', CHART_SPEC_LIMITS.maxSubtitleLength);
  if (subtitleError) return { ok: false, error: subtitleError };

  const dataResult = validateData(value.data);
  if ('code' in dataResult) return { ok: false, error: dataResult };
  if (!isObject(value.encoding)) return fail('invalid_encoding', 'encoding must be an object', '$.encoding');
  const rawEncoding = value.encoding;

  const chartType = value.chartType as YueChartType;
  const encoding: YueChartSpec['encoding'] = {};

  const requireField = (key: 'x' | 'y' | 'category' | 'value', types: ChartFieldType[]) => {
    const parsed = validateFieldEncoding(rawEncoding[key], `$.encoding.${key}`, types, dataResult.fields);
    if ('code' in parsed) return parsed;
    encoding[key] = parsed;
    return null;
  };

  if (chartType === 'bar' || chartType === 'line' || chartType === 'area') {
    const xError = requireField('x', ['category', 'time']);
    if (xError) return { ok: false, error: xError };
    const yError = requireField('y', ['number']);
    if (yError) return { ok: false, error: yError };
  } else if (chartType === 'scatter') {
    const xError = requireField('x', ['number']);
    if (xError) return { ok: false, error: xError };
    const yError = requireField('y', ['number']);
    if (yError) return { ok: false, error: yError };
  } else if (chartType === 'pie') {
    const categoryError = requireField('category', ['category']);
    if (categoryError) return { ok: false, error: categoryError };
    const valueError = requireField('value', ['number']);
    if (valueError) return { ok: false, error: valueError };
  } else if (chartType === 'stacked-bar' || chartType === 'multi-line') {
    const xError = requireField('x', ['category', 'time']);
    if (xError) return { ok: false, error: xError };
    const series = validateSeries(rawEncoding.series, dataResult.fields);
    if ('code' in series) return { ok: false, error: series };
    encoding.series = series;
  }

  if (rawEncoding.color !== undefined) {
    const color = validateFieldEncoding(rawEncoding.color, '$.encoding.color', ['category'], dataResult.fields);
    if ('code' in color) return { ok: false, error: color };
    encoding.color = color;
  }

  const presentation = validatePresentation(value.presentation, dataResult.fields);
  if (presentation && 'code' in presentation) return { ok: false, error: presentation };

  return {
    ok: true,
    spec: {
      version: 1,
      kind: 'chart',
      chartType,
      ...(typeof value.title === 'string' ? { title: value.title } : {}),
      ...(typeof value.subtitle === 'string' ? { subtitle: value.subtitle } : {}),
      data: dataResult.rows,
      encoding,
      ...(presentation ? { presentation } : {}),
    },
  };
}

export function parseYueChartSpec(raw: string): ChartSpecValidationResult {
  if (byteLength(raw) > CHART_SPEC_LIMITS.maxSerializedBytes) {
    return fail('payload_too_large', `Chart spec exceeds ${CHART_SPEC_LIMITS.maxSerializedBytes} bytes`);
  }
  try {
    return validateYueChartSpec(JSON.parse(raw));
  } catch {
    return fail('invalid_json', 'Chart spec must be valid JSON');
  }
}
