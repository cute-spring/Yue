export const MAX_ATTACHMENT_COUNT = 10;
export const MAX_ATTACHMENT_SIZE_BYTES = 20 * 1024 * 1024;

const DEFAULT_SUPPORTED_ATTACHMENT_MIME_TYPES = [
  'application/pdf',
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
  'application/vnd.ms-excel',
  'text/csv',
  'image/png',
  'image/jpeg',
  'image/gif',
  'image/webp',
];

const DEFAULT_SUPPORTED_ATTACHMENT_EXTENSIONS = [
  '.pdf',
  '.xlsx',
  '.xls',
  '.csv',
  '.png',
  '.jpg',
  '.jpeg',
  '.gif',
  '.webp',
];

export type UploadPolicy = {
  maxFiles: number;
  maxFileSizeBytes: number;
  allowedMimeTypes: string[];
  allowedExtensions: string[];
};

export type UploadPolicyPayload = {
  max_files?: number;
  max_file_size_bytes?: number;
  allowed_mime_types?: string[];
  allowed_extensions?: string[];
};

export const DEFAULT_UPLOAD_POLICY: UploadPolicy = {
  maxFiles: MAX_ATTACHMENT_COUNT,
  maxFileSizeBytes: MAX_ATTACHMENT_SIZE_BYTES,
  allowedMimeTypes: [...DEFAULT_SUPPORTED_ATTACHMENT_MIME_TYPES],
  allowedExtensions: [...DEFAULT_SUPPORTED_ATTACHMENT_EXTENSIONS],
};

export const getFileExtension = (name: string): string => {
  const dot = name.lastIndexOf('.');
  if (dot < 0) return '';
  return name.slice(dot).toLowerCase();
};

export const isImageFile = (file: Pick<File, 'type'>): boolean => file.type.startsWith('image/');

const normalizeAllowedList = (value: unknown): string[] => {
  if (!Array.isArray(value)) return [];
  return value
    .filter((item): item is string => typeof item === 'string')
    .map((item) => item.trim().toLowerCase())
    .filter((item) => item.length > 0);
};

const uniqueOrdered = (items: string[]): string[] => {
  const dedup = new Set<string>();
  items.forEach((item) => dedup.add(item));
  return Array.from(dedup.values());
};

export const resolveUploadPolicy = (payload?: UploadPolicyPayload | null): UploadPolicy => {
  const maxFiles = typeof payload?.max_files === 'number' && payload.max_files > 0
    ? payload.max_files
    : DEFAULT_UPLOAD_POLICY.maxFiles;
  const maxFileSizeBytes = typeof payload?.max_file_size_bytes === 'number' && payload.max_file_size_bytes > 0
    ? payload.max_file_size_bytes
    : DEFAULT_UPLOAD_POLICY.maxFileSizeBytes;
  const allowedMimeTypes = normalizeAllowedList(payload?.allowed_mime_types);
  const allowedExtensions = normalizeAllowedList(payload?.allowed_extensions);
  return {
    maxFiles,
    maxFileSizeBytes,
    allowedMimeTypes: allowedMimeTypes.length > 0 ? uniqueOrdered(allowedMimeTypes) : [...DEFAULT_UPLOAD_POLICY.allowedMimeTypes],
    allowedExtensions: allowedExtensions.length > 0 ? uniqueOrdered(allowedExtensions) : [...DEFAULT_UPLOAD_POLICY.allowedExtensions],
  };
};

const createSupportSets = (policy: UploadPolicy): { mimeTypes: Set<string>; extensions: Set<string> } => ({
  mimeTypes: new Set(policy.allowedMimeTypes.map((item) => item.toLowerCase())),
  extensions: new Set(policy.allowedExtensions.map((item) => item.toLowerCase())),
});

const formatLimitMb = (bytes: number): string => {
  const value = bytes / 1024 / 1024;
  return Number.isInteger(value) ? `${value}MB` : `${value.toFixed(2)}MB`;
};

export const getTooManyFilesWarningMessage = (maxFiles: number): string => `最多选择 ${maxFiles} 个附件`;

export const getOversizedWarningMessage = (maxFileSizeBytes: number): string =>
  `部分文件超过 ${formatLimitMb(maxFileSizeBytes)} 大小限制，已忽略`;

export const getAcceptAttributeFromPolicy = (policy: UploadPolicy): string => {
  const extensions = policy.allowedExtensions.map((item) => item.toLowerCase());
  const mimeTypes = policy.allowedMimeTypes.map((item) => item.toLowerCase());
  return [...extensions, ...mimeTypes].join(',');
};

export const isSupportedAttachment = (
  file: Pick<File, 'name' | 'type'>,
  policy: UploadPolicy = DEFAULT_UPLOAD_POLICY,
): boolean => {
  const sets = createSupportSets(policy);
  const mime = (file.type || '').toLowerCase();
  const extension = getFileExtension(file.name || '');
  if (mime.startsWith('image/')) return true;
  return sets.mimeTypes.has(mime) || sets.extensions.has(extension);
};

export const filterSupportedAttachments = (
  files: File[],
  policy: UploadPolicy = DEFAULT_UPLOAD_POLICY,
): { accepted: File[]; rejectedCount: number } => {
  const accepted = files.filter((file) => isSupportedAttachment(file, policy));
  return { accepted, rejectedCount: files.length - accepted.length };
};

export const mergeAttachments = (
  existing: File[],
  incoming: File[],
  maxCount: number,
  maxSizeBytes: number,
  policy: UploadPolicy = DEFAULT_UPLOAD_POLICY,
): { files: File[]; oversizedCount: number; overflowCount: number; unsupportedCount: number } => {
  const { accepted, rejectedCount } = filterSupportedAttachments(incoming, policy);
  const validIncoming = accepted.filter((file) => file.size <= maxSizeBytes);
  const oversizedCount = accepted.length - validIncoming.length;
  const merged = [...existing, ...validIncoming];
  const files = merged.slice(0, maxCount);
  const overflowCount = Math.max(0, merged.length - maxCount);
  return { files, oversizedCount, overflowCount, unsupportedCount: rejectedCount };
};

export const getUploadButtonClass = (attachmentCount: number): string => {
  if (attachmentCount > 0) {
    return 'relative p-2.5 bg-primary/20 text-primary border border-primary/30 rounded-2xl transition-all active:scale-90 shadow-sm';
  }
  return 'relative p-2.5 text-slate-500 hover:text-primary hover:bg-primary/10 rounded-2xl transition-all active:scale-90';
};

export const removeAttachmentAt = (files: File[], index: number): File[] => {
  return files.filter((_, itemIndex) => itemIndex !== index);
};

type ClipboardFileLike = {
  kind: string;
  type: string;
  getAsFile: () => File | null;
};

type ClipboardDataLike = {
  files?: ArrayLike<File>;
  items?: ArrayLike<ClipboardFileLike>;
};

export const extractClipboardFiles = (clipboardData: ClipboardDataLike | null | undefined): File[] => {
  if (!clipboardData) return [];

  const fromFiles = Array.from(clipboardData.files || []).filter((file) => isSupportedAttachment(file));
  const fromItems = Array.from(clipboardData.items || [])
    .filter((item) => item.kind === 'file')
    .map((item) => item.getAsFile())
    .filter((file): file is File => file instanceof File)
    .filter((file) => isSupportedAttachment(file));
  const dedup = new Map<string, File>();
  [...fromFiles, ...fromItems].forEach((file) => {
    const key = `${file.name}::${file.type}::${file.size}`;
    dedup.set(key, file);
  });
  return Array.from(dedup.values());
};

export const splitAttachmentsByType = (files: File[]): { imageFiles: File[]; nonImageFiles: File[] } => {
  const imageFiles = files.filter(isImageFile);
  const nonImageFiles = files.filter((file) => !isImageFile(file));
  return { imageFiles, nonImageFiles };
};

export const getVisionCapabilityHint = (
  hasSelectedModel: boolean,
  supportsVision: boolean,
  imageCount: number,
): string => {
  if (!hasSelectedModel || imageCount === 0 || supportsVision) return '';
  return '当前模型不支持图片理解能力，本次图片不会被分析；PDF/表格附件不受这条提示直接约束。';
};

export const getAttachmentCompositionHint = (imageCount: number, documentCount: number): string => {
  const totalCount = imageCount + documentCount;
  if (totalCount === 0) return '';

  const parts: string[] = [];
  if (imageCount > 0) parts.push(`${imageCount} 张图片`);
  if (documentCount > 0) parts.push(`${documentCount} 个文档`);
  return `已选择 ${totalCount} 个附件：${parts.join('，')}`;
};
