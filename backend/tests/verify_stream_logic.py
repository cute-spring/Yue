import json
import asyncio
from typing import List, Dict, Any

def simulate_sse_stream(data_items: List[Dict[str, Any]], chunk_size: int = 10):
    """
    模拟 SSE 流，故意在 JSON 中间切分 chunk
    """
    full_stream = ""
    for item in data_items:
        full_stream += f"data: {json.dumps(item)}\n\n"
    
    # 将完整的流切成固定大小的块，模拟网络分片
    chunks = [full_stream[i:i+chunk_size] for i in range(0, len(full_stream), chunk_size)]
    return chunks

class MockDecoder:
    def __init__(self):
        self.stream_mode = False
    
    def decode(self, value: str, stream: bool = False):
        self.stream_mode = stream
        return value

def test_parser_logic(chunks: List[str]):
    """
    模拟 useChatState.ts 中的解析逻辑
    """
    line_remainder = ""
    processed_data = []
    
    def process_line(line: str):
        if not line.trim() or not line.startswith('data: '):
            return
        try:
            data = json.loads(line[6:])
            processed_data.append(data)
        except Exception as e:
            print(f"FAILED TO PARSE: {line}")
            raise e

    # JavaScript 逻辑模拟
    for chunk in chunks:
        combined = line_remainder + chunk
        # 模拟 JS 的 split('\n')
        lines = combined.split('\n')
        line_remainder = lines.pop()
        
        for line in lines:
            # 模拟 JS 的 trim() 和 startsWith
            stripped_line = line.strip()
            if not stripped_line or not stripped_line.startswith('data: '):
                continue
            try:
                # 模拟 JSON.parse(line.slice(6))
                data = json.loads(stripped_line[6:])
                processed_data.append(data)
            except Exception as e:
                print(f"Error parsing line: [{line}]")
                print(f"Combined was: [{combined}]")
                print(f"Remainder was: [{line_remainder}]")
                raise e
    
    return processed_data

if __name__ == "__main__":
    # 模拟包含 HTML 标签的数据，这种数据通常较长，容易跨 chunk
    test_data = [
        {"content": "<!DOCTYPE html>\n"},
        {"content": "<html lang=\"en\">\n"},
        {"content": "<head>\n    <meta charset=\"UTF-8\">\n"},
        {"content": "    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">\n"},
        {"content": "    <title>Coffee Shop</title>\n"},
        {"content": "</head>\n<body>\n"}
    ]
    
    print("Testing with various chunk sizes...")
    for size in range(5, 50, 7):
        print(f"--- Chunk Size: {size} ---")
        chunks = simulate_sse_stream(test_data, chunk_size=size)
        try:
            result = test_parser_logic(chunks)
            print(f"Success! Processed {len(result)} items.")
        except Exception as e:
            print(f"FAILED with chunk size {size}")
    
    # 特殊测试：多字节字符
    print("\n--- Testing Multi-byte Characters (Chinese) ---")
    chinese_data = [{"content": "你好，这是一段中文测试内容。"}]
    # 故意切分中文字符的字节（Python 字符串是 unicode，所以这里用 bytes 模拟）
    full_sse = f"data: {json.dumps(chinese_data[0])}\n\n"
    sse_bytes = full_sse.encode('utf-8')
    # 假设在第 15 个字节切分，这可能会切断一个中文字符
    byte_chunks = [sse_bytes[:15], sse_bytes[15:]]
    
    print("Simulating byte-level truncation...")
    # 这里模拟 JS 的 TextDecoder(stream=true)
    # 如果 TextDecoder 没有 stream=true，第一段 decode 会产生乱码，第二段也会
    # 但如果有 stream=true，它会缓冲不完整的字节
    
    # 在 Python 中模拟：
    import codecs
    decoder = codecs.getincrementaldecoder('utf-8')()
    
    decoded_text = ""
    line_remainder = ""
    processed_chinese = []
    
    for b_chunk in byte_chunks:
        # stream=True in JS is equivalent to not setting final=True in Python's incremental decoder
        chunk_text = decoder.decode(b_chunk, final=False)
        combined = line_remainder + chunk_text
        lines = combined.split('\n')
        line_remainder = lines.pop()
        for line in lines:
            trimmed = line.strip()
            if trimmed.startswith('data: '):
                processed_chinese.append(json.loads(trimmed[6:]))
    
    # 扫尾
    chunk_text = decoder.decode(b'', final=True)
    combined = line_remainder + chunk_text
    trimmed = combined.strip()
    if trimmed.startswith('data: '):
        processed_chinese.append(json.loads(trimmed[6:]))
        
    print(f"Chinese Processed: {processed_chinese[0]['content'] if processed_chinese else 'FAILED'}")

    # 新增测试：SSE 协议中的空行和脏数据
    print("\n--- Testing SSE Protocol Robustness (Empty lines & dirty data) ---")
    dirty_stream = "data: {\"a\": 1}\n\n\n\n   \ndata: {\"b\": 2}\n\n"
    dirty_chunks = [dirty_stream]
    try:
        results = test_parser_logic(dirty_chunks)
        print(f"Success! Processed {len(results)} items from dirty stream.")
    except Exception as e:
        print(f"FAILED dirty stream test: {e}")
