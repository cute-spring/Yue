import { Attachment } from '../../types';

type UploadErrorPayload = {
  detail?: {
    code?: string;
    message?: string;
    max_files?: number;
    max_file_size_bytes?: number;
    allowed_mime_types?: string[];
    allowed_extensions?: string[];
  };
};

const MAX_UPLOAD_FILES_FALLBACK = 10;
const MAX_UPLOAD_FILE_SIZE_FALLBACK_BYTES = 20 * 1024 * 1024;

const formatLimitMb = (bytes: number): string => {
  const value = bytes / 1024 / 1024;
  return Number.isInteger(value) ? `${value}MB` : `${value.toFixed(2)}MB`;
};

const getUploadErrorMessage = (detail?: UploadErrorPayload['detail']): string => {
  const code = detail?.code;
  switch (code) {
    case 'unsupported_file_type':
      return '附件上传失败：文件类型不支持（仅支持图片/PDF/Excel/CSV）';
    case 'too_many_files':
      return `附件上传失败：单次最多上传 ${detail?.max_files || MAX_UPLOAD_FILES_FALLBACK} 个文件`;
    case 'file_too_large':
      return `附件上传失败：文件超过大小限制（${formatLimitMb(detail?.max_file_size_bytes || MAX_UPLOAD_FILE_SIZE_FALLBACK_BYTES)}）`;
    case 'empty_file':
      return '附件上传失败：存在空文件';
    default:
      return '附件上传失败，请稍后重试';
  }
};

export const uploadAttachments = async (
  files: File[],
  fetchImpl: (input: RequestInfo | URL, init?: RequestInit) => Promise<Response> = fetch,
): Promise<Attachment[]> => {
  if (files.length === 0) return [];
  const formData = new FormData();
  files.forEach((file) => formData.append('files', file));

  const response = await fetchImpl('/api/files', {
    method: 'POST',
    body: formData,
  });
  if (!response.ok) {
    let detail: UploadErrorPayload['detail'] | undefined;
    try {
      const payload = (await response.json()) as UploadErrorPayload;
      detail = payload?.detail;
    } catch {
      detail = undefined;
    }
    throw new Error(getUploadErrorMessage(detail));
  }
  const payload = (await response.json()) as { files?: Attachment[] };
  return Array.isArray(payload.files) ? payload.files : [];
};
