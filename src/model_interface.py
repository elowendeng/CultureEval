# src/model_interface.py
import openai
import base64
from PIL import Image
from io import BytesIO
from typing import Dict, Any
import os
import requests
import json
from zai import ZhipuAiClient
import hashlib
import hmac
import time
from urllib.parse import urlencode
import websocket
import ssl


def _image_to_base64_data(image_path: str) -> str:
    """Local image → base64 string (used for data URL)"""
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image not found: {image_path}")
    try:
        with Image.open(image_path).convert("RGB") as img:
            # Adjust size
            max_size = (1024, 1024)
            img.thumbnail(max_size, Image.Resampling.LANCZOS)
            buffer = BytesIO()
            img.save(buffer, format="JPEG", quality=85, optimize=True)
            # Check file size
            if buffer.getbuffer().nbytes > 4 * 1024 * 1024:
                buffer = BytesIO()
                img.save(buffer, format="JPEG", quality=75, optimize=True)
            b64 = base64.b64encode(buffer.getvalue()).decode()
            return b64
    except Exception as e:
        raise ValueError(f"Image processing failed: {str(e)}")
    finally:
        if 'buffer' in locals():
            buffer.close()


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
        # Generate RFC1123 format timestamp
        now = time.strftime('%a, %d %b %Y %H:%M:%S GMT', time.gmtime())
        # Build signature original string
        signature_origin = f"host: {self.host}\ndate: {now}\nGET {self.path} HTTP/1.1"
        # Use hmac-sha256 for encryption
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
        # Build request URL
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
                # Adjust size, ensuring the image size meets API requirements
                max_size = (1024, 1024)
                img.thumbnail(max_size, Image.Resampling.LANCZOS)
                buffer = BytesIO()
                img.save(buffer, format="JPEG", quality=85, optimize=True)
                # Check file size
                file_size = buffer.getbuffer().nbytes
                if file_size > 4 * 1024 * 1024:
                    buffer = BytesIO()
                    img.save(buffer, format="JPEG", quality=70, optimize=True)
                b64 = base64.b64encode(buffer.getvalue()).decode()
                return b64
        except Exception as e:
            raise ValueError(f"Image processing failed: {str(e)}")
        finally:
            if 'buffer' in locals():
                buffer.close()

    def predict(self, image_path, question=None):
        """Image Understanding Main Function"""
        base64_str = self._image_to_base64(image_path)
        # Must place the image first, then the text (order cannot be reversed!)
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
                    "max_tokens": 512,
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
                    print(f'\nRequest error: {code}, Error message: {data["header"]["message"]}')
                    ws.close()
                    return
                choices = data.get("payload", {}).get("choices", {})
                if choices:
                    status = choices["status"]
                    content = choices["text"][0]["content"]
                    result_text += content
                    if status == 2:  # End frame
                        ws.close()
            except Exception as e:
                print(f"\nParsing error: {e}")

        def on_error(ws, error):
            print(f"WebSocket error: {error}")

        def on_close(ws, *args):
            pass

        def on_open(ws):
            ws.send(json.dumps(request_data, ensure_ascii=False))

        try:
            ws_url = self._get_auth_url()
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
            print(f"Connection exception: {e}")
        finally:
            if ws:
                ws.close()
        return result_text.strip()


class MLLMInterface:
    def __init__(self, model_config: Dict[str, Any]):
        self.config = model_config
        self.model_type = model_config.get('type', 'api')
        if self.model_type == 'api':
            base_url = os.environ.get(model_config.get('base_url', ''))
            api_key = os.environ.get(model_config['api_key'])
            # Determine if it is an Alibaba Cloud model (qwen series)
            if 'qwen' in model_config['model_name']:
                self.client_type = 'aliyun'
                self.client = openai.OpenAI(
                    api_key=api_key,
                    base_url=base_url
                )
            elif 'ernie' in model_config['model_name']:
                # All other models use Baidu Qianfan API
                self.client_type = 'baidu'
                self.base_url = base_url
                self.api_key = api_key
            elif 'glm' in model_config['model_name']:
                # Zhipu AI API - does not require base_url
                self.client_type = 'zhipu'
                self.api_key = api_key
            elif 'spark' in model_config['model_name']:
                # iFlytek Spark API
                self.client_type = 'spark'
                self.app_id = model_config.get('app_id', '')
                self.api_key = api_key
                self.api_secret = os.environ.get(model_config['api_secret'])
        else:
            raise ValueError(f"Unsupported model type: {self.model_type}")

    def predict(self, image_path: str, question: str) -> str:
        if self.model_type == 'api':
            if self.client_type == 'aliyun':
                return self._predict_aliyun_api(image_path, question)
            elif self.client_type == 'baidu':
                return self._predict_baidu_api(image_path, question)
            elif self.client_type == 'zhipu':
                return self._predict_zhipu_api(image_path, question)
            elif self.client_type == 'spark':
                return self._predict_spark_api(image_path, question)
        else:
            raise ValueError(f"Unsupported model type: {self.model_type}")

    def _predict_aliyun_api(self, image_path: str, question: str) -> str:
        try:
            image_data = _image_to_base64_data(image_path)
            # Alibaba Cloud Multimodal Message Format
            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_data}"  # Complete data URL
                            }
                        },
                        {
                            "type": "text",  # Must explicitly specify type
                            "text": question
                        }
                    ]
                }
            ]
            response = self.client.chat.completions.create(
                model=self.config['model_name'],
                messages=messages,
                max_tokens=512,
                temperature=0.3
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            return f"[API Error] {str(e)}"

    def _predict_baidu_api(self, image_path: str, question: str) -> str:
        try:
            image_data = _image_to_base64_data(image_path)
            # Baidu Qianfan API Format
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {self.api_key}'
            }
            payload = json.dumps({
                "model": self.config['model_name'],
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": question
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_data}"  # Complete data URL
                                }
                            }
                        ]
                    }
                ],
                "max_tokens": 512,
                "temperature": 0.3,
                "stream": False
            })
            response = requests.request("POST", self.base_url, headers=headers, data=payload)
            result = response.json()
            return result['choices'][0]['message']['content']
        except Exception as e:
            return f"[Baidu Qianfan API Error] {str(e)}"

    def _predict_zhipu_api(self, image_path: str, question: str) -> str:
        try:
            image_data = _image_to_base64_data(image_path)
            # Zhipu AI API Format
            client = ZhipuAiClient(api_key=self.api_key)
            payload = client.chat.completions.create(
                model=self.config['model_name'],
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": image_data
                                }
                            },
                            {
                                "type": "text",
                                "text": question
                            }
                        ]
                    }
                ],
                max_tokens=512,
                temperature=0.3
            )
            return payload.choices[0].message.content.strip()
        except Exception as e:
            return f"[Baidu Qianfan API Error] {str(e)}"

    def _predict_spark_api(self, image_path: str, question: str) -> str:
        try:
            client = SparkImageUnderstanding(
                app_id=self.app_id,
                api_key=self.api_key,
                api_secret=self.api_secret
            )
            result = client.predict(image_path, question)
            return result
        except Exception as e:
            return f"[Spark API Error] {str(e)}"