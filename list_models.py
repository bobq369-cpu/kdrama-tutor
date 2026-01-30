"""Google AI API에서 사용 가능한 모델 목록 확인 스크립트.
실행: set GOOGLE_API_KEY=키값 && python list_models.py
"""
import os
import google.generativeai as genai

def main():
    key = os.environ.get("GOOGLE_API_KEY")
    if not key:
        print("GOOGLE_API_KEY를 환경변수로 설정해주세요. (예: set GOOGLE_API_KEY=키값)")
        return
    genai.configure(api_key=key)
    print("사용 가능한 모델 (generateContent 지원):")
    for m in genai.list_models():
        if "generateContent" in (m.supported_generation_methods or []):
            print(f"  - {m.name}")
    print("\n위 모델명 중 'models/' 접두어 없이 사용하세요 (예: gemini-2.5-flash).")

if __name__ == "__main__":
    main()
