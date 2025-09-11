#!/usr/bin/env python3
"""
Тестовый скрипт для проверки работы OpenRouter API
"""

import os
from dotenv import load_dotenv
from models.text_editor.openrouter_client import OpenRouterService

def test_openrouter():
    # Загружаем переменные окружения
    load_dotenv()
    
    # Проверяем наличие ключа
    api_key = os.getenv('OPENROUTER_API_KEY')
    if not api_key:
        print("❌ OPENROUTER_API_KEY не найден в переменных окружения")
        print("Создайте файл .env в корне проекта со следующим содержимым:")
        print("OPENROUTER_API_KEY=your_actual_openrouter_api_key_here")
        return False
    
    print(f"✅ OPENROUTER_API_KEY найден: {api_key[:10]}...")
    
    try:
        # Создаем сервис
        service = OpenRouterService()
        print("✅ OpenRouterService создан успешно")
        
        # Тестируем простой запрос
        import asyncio
        
        async def test_request():
            response = await service.analyze_text(
                prompt="Ответь кратко: 'Привет!'",
                text="",
                expect_json=False
            )
            print(f"✅ Тестовый запрос выполнен: {response[:50]}...")
            return True
        
        result = asyncio.run(test_request())
        return result
        
    except Exception as e:
        print(f"❌ Ошибка при тестировании OpenRouter: {e}")
        return False

if __name__ == "__main__":
    print("Тестирование OpenRouter API...")
    success = test_openrouter()
    if success:
        print("🎉 OpenRouter настроен и работает!")
    else:
        print("💥 Проблемы с настройкой OpenRouter")
