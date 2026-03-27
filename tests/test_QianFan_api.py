# tests/test_QianFan_api.py
import json
import requests
import os
import time
import random
from tests.pre_process import load_environment, get_env_variable, _image_to_base64_data


def test_qianfan(key, url, name, image_path: str, question: str, max_retries=3) -> str:
    for attempt in range(max_retries):
        try:
            image_data = _image_to_base64_data(image_path)
            payload = json.dumps({
                "model": name,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_data}"
                                }
                            },
                            {
                                "type": "text",
                                "text": question
                            }
                        ]
                    }
                ],
                "max_tokens": 512,
                "temperature": 0.3,
                "stream": False
            })
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {key}'
            }
            print(f"This is the {attempt + 1}th attempt to send a request...")
            response = requests.request("POST", url, headers=headers, data=payload, timeout=30)
            print(f"HTTP status code: {response.status_code}.")
            # Processing rate limit error
            if response.status_code == 429:
                wait_time = (2 ** attempt) + random.uniform(0, 1)  # exponential backoff
                print(f"Rate limiting, retrying after {wait_time:.2f} seconds...")
                time.sleep(wait_time)
                continue
            result = response.json()
            if response.status_code != 200:
                error_msg = result.get('error', {}).get('message', 'Unknown error') if isinstance(result, dict) else str(result)
                return f"[Baidu Qianfan API Error] HTTP {response.status_code}: {error_msg}"
            # Check the response structure
            if "choices" not in result:
                return f"[Baidu Qianfan API Error] Unexpected response format: {result}"
            if not result["choices"]:
                return "[Baidu Qianfan API Error] Empty choices in response"
            if "message" not in result["choices"][0]:
                return f"[Baidu Qianfan API Error] No message in choice: {result['choices'][0]}"
            if "content" not in result["choices"][0]["message"]:
                return f"[Baidu Qianfan API Error] No content in message: {result['choices'][0]['message']}"
            return result["choices"][0]["message"]["content"]
        except requests.exceptions.RequestException as e:
            if attempt == max_retries - 1:  # Last attempt
                return f"[Baidu Qianfan API Request Error] {str(e)}"
            wait_time = (2 ** attempt) + random.uniform(0, 1)
            print(f"The request failed. Retrying after {wait_time:.2f} seconds...")
            time.sleep(wait_time)
        except json.JSONDecodeError as e:
            return f"[Baidu Qianfan API JSON Error] {str(e)} - Response: {response.text if 'response' in locals() else 'N/A'}"
        except Exception as e:
            return f"[Baidu Qianfan API Unexpected Error] {str(e)}"
    return "[Baidu Qianfan API Error] Max retries exceeded due to rate limiting"


if __name__ == '__main__':
    load_environment()
    api_key = get_env_variable('BAIDU_API_KEY')
    base_url = get_env_variable('BAIDU_BASE_URL')
    # ernie-4.5-turbo-vl  qianfan-check-vl  llama-4-scout-17b-16e-instruct
    model_name = "ernie-4.5-turbo-vl"
    path = '/home/ubuntu/CultureEval/data/images/001.jpg'
    text = '请用一句话描述这张图片'
    print(f"Configuration check:")
    print(f"   API Key: {api_key[:10]}...")
    print(f"   Base URL: {base_url}")
    print(f"   Model Name: {model_name}")
    print(f"   Image path: {path}")
    print(f"   Does the image exist?: {os.path.exists(path)}")
    # Add request interval
    print("Add request intervals to avoid rate limiting...")
    time.sleep(2)  # Wait 2 seconds before each request
    result = test_qianfan(api_key, base_url, model_name, path, text)
    print(f"Final result: {result}")
