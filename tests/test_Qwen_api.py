# tests/test_Qwen_api.py
import openai
from tests.pre_process import load_environment, get_env_variable, _image_to_base64_data


def test_api_key(key, url, name):
    print("\nIs the test key valid?")
    try:
        client = openai.OpenAI(
            api_key=key,
            base_url=url
        )
        response = client.chat.completions.create(
            model=name,
            messages=[{"role": "user", "content": "Hello"}],
            max_tokens=10
        )
        print("The API key is valid!")
        print(f"Response: {response.choices[0].message.content}")
        return client
    except Exception as e:
        print(f"Invalid API key: {e}.")


def test_fixed_format(key, url, name1, name2):
    client = test_api_key(key, url, name1)
    # Test 1: Plain text format (correct Alibaba Cloud format)
    print("\nTesting plain text format...")
    try:
        messages = [
            {
                "role": "user",
                "content": "你好，请简单回复"  # Direct strings, not arrays
            }
        ]
        response = client.chat.completions.create(
            model=name1,
            messages=messages,
            max_tokens=10
        )
        print(f"Text test successful: {response.choices[0].message.content}")
    except Exception as e:
        print(f"Text test failed: {e}")
    # Test 2: Multimodal Formats (Image + Text)
    print("\nTesting multimodal formats...")
    try:
        img_data = _image_to_base64_data('your_path/CultureEval/data/images/001.jpg')
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{img_data}"  # Full data URL
                        }
                    },
                    {
                        "type": "text",
                        "text": "请用一句话描述这张图片"
                    }
                ]
            }
        ]
        response = client.chat.completions.create(
            model=name2,
            messages=messages,
            max_tokens=50
        )
        print(f"Multimodal testing successful: {response.choices[0].message.content}")
    except Exception as e:
        print(f"Multimodal test failed: {e}")


if __name__ == "__main__":
    load_environment()
    api_key = get_env_variable('DASHSCOPE_API_KEY')
    base_url = get_env_variable('DASHSCOPE_BASE_URL')
    model_name1 = "qwen-plus"
    model_name2 = "qwen-vl-max"
    test_fixed_format(api_key, base_url, model_name1, model_name2)
