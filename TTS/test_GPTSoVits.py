import os
from tts import infer_tts_get, infer_tts_post, set_gpt_weights, set_sovits_weights, restart_service
from dotenv import load_dotenv
load_dotenv("/home/yomu/agent/.env")

# Define a few test cases for the script to validate functionality
def test_infer_tts_get():
    print("\nRunning test_infer_tts_get...")
    test_content = "你好，欢迎使用我们的服务！"
    try:
        infer_tts_get(test_content)
        print("test_infer_tts_get passed.")
    except Exception as e:
        print(f"test_infer_tts_get failed with error: {e}")

def test_infer_tts_post():
    print("\nRunning test_infer_tts_post...")
    test_content = "这是一个测试，感谢您的合作！"
    try:
        infer_tts_post(test_content)
        print("test_infer_tts_post passed.")
    except Exception as e:
        print(f"test_infer_tts_post failed with error: {e}")

def test_set_gpt_weights():
    print("\nRunning test_set_gpt_weights...")
    test_gpt_weights_path = os.path.join("./GPT_weights_v2", "alxy_all_modified_v1.0-e45.ckpt")
    try:
        set_gpt_weights(test_gpt_weights_path)
        print("test_set_gpt_weights passed.")
    except Exception as e:
        print(f"test_set_gpt_weights failed with error: {e}")

def test_set_sovits_weights():
    print("\nRunning test_set_sovits_weights...")
    test_sovits_weights_path = os.path.join("./SoVITS_weights_v2", "alxy_all_e18_s3420.pth")
    try:
        set_sovits_weights(test_sovits_weights_path)
        print("test_set_sovits_weights passed.")
    except Exception as e:
        print(f"test_set_sovits_weights failed with error: {e}")

def test_restart_service():
    print("\nRunning test_restart_service...")
    try:
        restart_service()
        print("test_restart_service passed.")
    except Exception as e:
        print(f"test_restart_service failed with error: {e}")

if __name__ == "__main__":
    # Run all the tests
    test_infer_tts_get()
    test_infer_tts_post()
    # test_set_gpt_weights()
    # test_set_sovits_weights()
    # test_restart_service()
    print("\nAll tests completed.")
