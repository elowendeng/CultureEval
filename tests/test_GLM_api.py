# tests/test_GLM_api.py
from zai import ZhipuAiClient
from tests.pre_process import load_environment, get_env_variable, _image_to_base64_data


def test_api():
    load_environment()
    key = get_env_variable('GLM_API_KEY')
    client = ZhipuAiClient(api_key=key)
    path = '/home/ubuntu/CultureEval/data/images/001.jpg'
    question = '请用一句话描述这张图片'
    image_data = _image_to_base64_data(path)
    response = client.chat.completions.create(
        # glm-4.5v  glm-4.1v-thinking-flashx  glm-4v-plus-0111
        model="glm-4v-plus-0111",
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
        thinking={
            "type": "enabled"
        }
    )
    # Output only the content
    print(response.choices[0].message.content.strip())


if __name__ == '__main__':
    test_api()
