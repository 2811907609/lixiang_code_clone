from pathlib import Path
from typing import Optional

import chardet


def detect_byte_content_encoding(data: bytes, confidence_threshold: float = 0.7) -> Optional[str]:
    """
    基于字节内容检测编码的抽象方法

    结合了chardet检测和多种备用编码的优势，提供更可靠的编码检测

    Args:
        data: 要检测编码的字节数据
        confidence_threshold: chardet检测结果的最小置信度阈值，默认0.7

    Returns:
        检测到的编码名称，如果无法检测则返回None
    """

    # 结合中文环境常用编码和国际通用编码
    fallback_encodings = ['utf-8', 'gbk', 'gb2312', 'latin-1', 'cp1252', 'ascii']

    if not data:
        return "utf-8"  # 空数据默认返回utf-8

    try:
        # 使用chardet进行初始检测
        result = chardet.detect(data)
        encoding = result.get('encoding')
        confidence = result.get('confidence', 0)

        # 如果chardet检测结果置信度足够高，直接返回
        if encoding and confidence > confidence_threshold:
            return encoding

        # 置信度不够时，尝试常见编码进行验证

        for test_encoding in fallback_encodings:
            try:
                data.decode(test_encoding)
                return test_encoding
            except UnicodeDecodeError:
                continue

        # 如果所有编码都失败，返回None
        return None

    except Exception as e:
        print(f"编码检测过程中发生错误: {e}")
        return None


def detect_file_encoding(file_path: Path, min_file_size: int = 81920) -> Optional[str]:
    """
    Detect the encoding of a file using chardet.
    Reuses the same logic as file_reader.py
    """
    try:
        with open(file_path, 'rb') as f:
            # Read a sample of the file for encoding detection
            sample_size = min(min_file_size, file_path.stat().st_size)
            raw_data = f.read(sample_size)
        encoding = detect_byte_content_encoding(raw_data)
        return encoding
    except Exception as e:
        print(f"Failed to detect encoding for {file_path}: {e}")
        return None


# 处理输出，安全解码
def safe_decode_byte_data(data: bytes) -> str:
    """安全解码字节数据为字符串"""
    if not data:
        return ""

    encoding_type = detect_byte_content_encoding(data)
    if encoding_type:
        return data.decode(encoding_type)
    else:
        # 如果所有编码都失败，使用错误处理方式
        return data.decode('utf-8', errors='replace')
