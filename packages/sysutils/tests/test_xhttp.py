from unittest.mock import MagicMock, patch

from sysutils.xhttp import HttpResponse, encode_header_value, post_json


def test_post_json():
    msg = dict(
        msg_type='text',
        content=dict(text='hi'),
    )
    url = 'http://localhost:8080/api/test'

    # Mock the urllib.request.urlopen
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.read.return_value = b'{"success": true}'
    mock_response.__enter__.return_value = mock_response

    with patch('urllib.request.urlopen', return_value=mock_response):
        res = post_json(url, msg)
        assert res.status == 200
        assert res.ok()
        assert res.json() == {"success": True}


def test_post_json_with_custom_headers():
    data = {"key": "value"}
    url = "http://example.com/api"
    headers = {"Authorization": "Bearer token123"}

    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.read.return_value = b'{"status": "ok"}'
    mock_response.__enter__.return_value = mock_response

    with patch('urllib.request.Request') as mock_request, \
         patch('urllib.request.urlopen', return_value=mock_response):
        res = post_json(url, data, headers)

        # Verify headers were properly set
        _, kwargs = mock_request.call_args
        assert kwargs['headers']['Authorization'] == "Bearer token123"
        assert kwargs['headers']['Content-Type'] == "application/json"
        assert res.json() == {"status": "ok"}


def test_post_json_error_response():
    data = {"test": "data"}
    url = "http://example.com/api"

    # Create mock HTTP error response
    mock_response = MagicMock()
    mock_response.status = 400
    mock_response.read.return_value = b'{"error": "Bad request"}'
    mock_response.__enter__.return_value = mock_response

    with patch('urllib.request.urlopen', return_value=mock_response):
        res = post_json(url, data)
        assert res.status == 400
        assert not res.ok()
        assert res.json() == {"error": "Bad request"}


def test_http_response_methods():
    # Test HttpResponse class methods directly
    response = HttpResponse(status=200, _content=b'{"data": "test"}')

    assert response.ok()
    assert response.text() == '{"data": "test"}'
    assert response.json() == {"data": "test"}

    # Test caching of text conversion
    response._text = "cached text"
    assert response.text() == "cached text"


def test_encode_header_value_ascii():
    """测试ASCII字符不需要编码"""
    assert encode_header_value("hello") == "hello"
    assert encode_header_value("Content-Type") == "Content-Type"
    assert encode_header_value("application/json") == "application/json"


def test_encode_header_value_empty():
    """测试空值处理"""
    assert encode_header_value("") == ""
    assert encode_header_value(None) is None


def test_encode_header_value_unicode():
    """测试Unicode字符编码"""
    # 中文字符
    assert encode_header_value("你好") == "%E4%BD%A0%E5%A5%BD"
    # 日文
    assert encode_header_value("こんにちは") == "%E3%81%93%E3%82%93%E3%81%AB%E3%81%A1%E3%81%AF"
    # Emoji
    assert encode_header_value("🌟") == "%F0%9F%8C%9F"


def test_encode_header_value_mixed():
    """测试混合字符编码"""
    assert encode_header_value("Hello 世界") == "Hello%20%E4%B8%96%E7%95%8C"
    assert encode_header_value("API-Key: 12345") == "API-Key: 12345"  # ASCII字符不编码
    assert encode_header_value("path/to/file.txt") == "path/to/file.txt"  # ASCII字符不编码


def test_encode_header_value_special_chars():
    """测试特殊字符处理"""
    # 空格 - ASCII字符不编码
    assert encode_header_value("hello world") == "hello world"
    # 特殊符号 - ASCII字符不编码
    assert encode_header_value("test@example.com") == "test@example.com"
    assert encode_header_value("key=value") == "key=value"
    # 保留的安全字符 - ASCII字符不编码
    assert encode_header_value("http://example.com/path") == "http://example.com/path"
