# tests/test_Spark_api.py
import base64
import hashlib
import hmac
import json
import time
from urllib.parse import urlencode
import websocket
import ssl
import os
from PIL import Image
from io import BytesIO
from tests.pre_process import load_environment, get_env_variable


class SparkImageUnderstanding:
    def __init__(self, app_id, api_key, api_secret):
        self.app_id = app_id
        self.api_key = api_key
        self.api_secret = api_secret
        # Use the correct host and path according to the documentation.
        self.host = 'spark-api.cn-huabei-1.xf-yun.com'
        self.path = '/v2.1/image'

    def _get_auth_url(self):
        """Generate authentication URL - according to the official documentation format"""
        # Generate timestamps in RFC1123 format
        now = time.strftime('%a, %d %b %Y %H:%M:%S GMT', time.gmtime())
        # Construct the original signature string
        signature_origin = f"host: {self.host}\ndate: {now}\nGET {self.path} HTTP/1.1"
        # Encrypt using hmac-sha256
        signature_sha = hmac.new(
            self.api_secret.encode('utf-8'),
            signature_origin.encode('utf-8'),
            digestmod=hashlib.sha256
        ).digest()
        # base64 encoding
        signature_sha_base64 = base64.b64encode(signature_sha).decode('utf-8')
        # Build authorization parameters
        authorization_origin = f'api_key="{self.api_key}", algorithm="hmac-sha256", headers="host date request-line", signature="{signature_sha_base64}"'
        authorization = base64.b64encode(authorization_origin.encode('utf-8')).decode('utf-8')
        # Build the request URL
        v = {
            "authorization": authorization,
            "date": now,
            "host": self.host
        }
        url = f"wss://{self.host}{self.path}?{urlencode(v)}"
        return url

    def _image_to_base64(self, image_path):
        """Local image → base64 string"""
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image not found: {image_path}")
        try:
            with Image.open(image_path).convert("RGB") as img:
                # Adjust the size to ensure the image meets API requirements.
                max_size = (1024, 1024)
                img.thumbnail(max_size, Image.Resampling.LANCZOS)
                buffer = BytesIO()
                img.save(buffer, format="JPEG", quality=85, optimize=True)
                # Check file size
                file_size = buffer.getbuffer().nbytes
                print(f"Image size after processing: {file_size / 1024:.2f} KB")
                if file_size > 4 * 1024 * 1024:
                    print("Image too large, recompressed...")
                    buffer = BytesIO()
                    img.save(buffer, format="JPEG", quality=70, optimize=True)
                    file_size = buffer.getbuffer().nbytes
                    print(f"Size after recompression: {file_size / 1024:.2f} KB")
                b64 = base64.b64encode(buffer.getvalue()).decode()
                return b64
        except Exception as e:
            raise ValueError(f"Image processing failed: {str(e)}")
        finally:
            if 'buffer' in locals():
                buffer.close()

    def understand_image(self, image_path, question=None):
        """Image Understanding Main Function"""
        print(f"Question: {question or 'No question'}")
        print(f"Image path: {image_path}")
        # Returns only plain base64, without any prefix.
        base64_str = self._image_to_base64(image_path)
        # You must place the image first, then the text (the order cannot be reversed!)
        text_array = [
            {
                "role": "user",
                "content": base64_str,          # ← Pure base64, no prefix!
                "content_type": "image"
            }
        ]
        if question:
            text_array.append({
                "role": "user",
                "content": question,
                "content_type": "text"
            })
        request_data = {
            "header": {
                "app_id": self.app_id,
                "uid": "user001"
            },
            "parameter": {
                "chat": {
                    "domain": "imagev3",        # imagev3 (highest version)
                    "temperature": 0.5,
                    "max_tokens": 2048,
                    "auditing": "default"
                }
            },
            "payload": {
                "message": {
                    "text": text_array
                }
            }
        }
        result_text = ""
        ws = None

        def on_message(ws, message):
            nonlocal result_text
            try:
                data = json.loads(message)
                code = data['header']['code']
                if code != 0:
                    print(f'\nRequest error: {code}, Error message: {data["header"]["message"]}.')
                    ws.close()
                    return
                choices = data.get("payload", {}).get("choices", {})
                if choices:
                    status = choices["status"]
                    content = choices["text"][0]["content"]
                    result_text += content
                    print(content, end='')

                    if status == 2:  # End frame
                        print("\nComplete results received.")
                        ws.close()
            except Exception as e:
                print(f"\nParsing error: {e}")

        def on_error(ws, error):
            print(f"WebSocket error: {error}")

        def on_close(ws, *args):
            print("WebSocket has been closed.")

        def on_open(ws):
            print("WebSocket connection successful, sending request...")
            ws.send(json.dumps(request_data, ensure_ascii=False))

        try:
            ws_url = self._get_auth_url()
            print(f"Connection URL: {ws_url.split('?')[0]}")
            ws = websocket.WebSocketApp(
                ws_url,
                on_message=on_message,
                on_error=on_error,
                on_close=on_close,
                on_open=on_open
            )
            ws.run_forever(
                sslopt={"cert_reqs": ssl.CERT_NONE},
                ping_interval=30,
                ping_timeout=10
            )
        except Exception as e:
            print(f"Connection error: {e}")
        finally:
            if ws:
                ws.close()
        return result_text.strip()


# test function
def test_api_connection():
    """Test API connection"""
    print("Testing API connection...")
    load_environment()
    try:
        api_key = get_env_variable('SPARK_API_KEY')
        app_id = "35007571"
        api_secret = "MTEwNDg4Nzg3OTI0NzgwNzQxMTEzYTkz"
        print("Verification credentials...")
        print(f"   APP_ID: {app_id}")
        print(f"   API_KEY: {api_key[:8]}...")
        print(f"   API_SECRET: {api_secret[:8]}...")
        # Initialize client
        client = SparkImageUnderstanding(app_id, api_key, api_secret)
        # Test image path
        image_path = '/home/ubuntu/CultureEval/data/images/001.jpg'
        if not os.path.exists(image_path):
            print(f"The image file does not exist: {image_path}")
            # Try creating a test image
            try:
                from PIL import Image, ImageDraw
                test_img = Image.new('RGB', (100, 100), color='red')
                test_img.save('test_image.jpg')
                image_path = 'test_image.jpg'
                print("Test image created.")
            except:
                print("Unable to create test image.")
                return
        print(f"Use images: {image_path}")
        # Test issues
        question = "请用一句话描述这张图片"
        result = client.understand_image(image_path, question)
        if result:
            print(f"Test successful: {result}")
        else:
            print("Test failed: No results returned.")
    except Exception as e:
        print(f"Test process error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_api_connection()
