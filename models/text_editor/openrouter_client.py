import asyncio
import logging
import os
from typing import Optional

import httpx

logger = logging.getLogger(__name__)


class OpenRouterService:
    def __init__(self, model: str = 'anthropic/claude-3.5-haiku'):
        self.model = model
        self.api_key = os.getenv('OPENROUTER_API_KEY')
        if not self.api_key:
            raise ValueError('OPENROUTER_API_KEY environment variable is required')

        self.base_url = 'https://openrouter.ai/api/v1'
        self.headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
            'HTTP-Referer': 'https://lightpitch.app',  # Optional: for tracking
            'X-Title': 'LightPitch',  # Optional: for tracking
        }

    def _extract_json(self, text: str) -> str:
        """Extract JSON from response text"""
        if '```json' in text:
            json_start = text.find('```json') + 7
            json_end = text.find('```', json_start)
            if json_end != -1:
                return text[json_start:json_end].strip()
        if '```' in text:
            json_start = text.find('```') + 3
            json_end = text.find('```', json_start)
            if json_end != -1:
                return text[json_start:json_end].strip()
        start_idx = text.find('{')
        if start_idx == -1:
            return text.strip()
        brace_count = 0
        for i, char in enumerate(text[start_idx:], start_idx):
            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0:
                    return text[start_idx : i + 1]
        return text.strip()

    async def analyze_text(self, prompt: str, text: str, expect_json: bool = False) -> str:
        """Analyze text using OpenRouter API"""
        messages = [{'role': 'system', 'content': prompt}, {'role': 'user', 'content': text}]

        payload = {
            'model': self.model,
            'messages': messages,
            'temperature': 0.3,
            'max_tokens': 2000,
        }

        # For Claude models, we can request JSON format
        if expect_json and 'claude' in self.model.lower():
            payload['response_format'] = {'type': 'json_object'}

        for attempt in range(3):
            try:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    response = await client.post(
                        f'{self.base_url}/chat/completions', headers=self.headers, json=payload
                    )
                    response.raise_for_status()

                    data = response.json()
                    content = data['choices'][0]['message']['content']

                    return self._extract_json(content) if expect_json else content

            except httpx.HTTPStatusError as e:
                error_str = str(e).lower()
                is_retryable = any(k in error_str for k in ['rate_limit', '429', '503', 'timeout', 'server_error'])

                if is_retryable and attempt < 2:
                    wait_time = 2 * (attempt + 1)
                    logger.warning(f'Retryable error, waiting {wait_time}s: {str(e)}')
                    await asyncio.sleep(wait_time)
                    continue

                logger.error(f'OpenRouter API HTTP error: {str(e)}')
                raise Exception(f'AI service error: {str(e)}')

            except Exception as e:
                error_str = str(e).lower()
                is_retryable = any(k in error_str for k in ['rate_limit', '429', '503', 'timeout', 'server_error'])

                if is_retryable and attempt < 2:
                    wait_time = 2 * (attempt + 1)
                    logger.warning(f'Retryable error, waiting {wait_time}s: {str(e)}')
                    await asyncio.sleep(wait_time)
                    continue

                logger.error(f'OpenRouter API error: {str(e)}')
                raise Exception(f'AI service error: {str(e)}')
