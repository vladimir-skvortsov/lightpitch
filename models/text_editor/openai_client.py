import asyncio
import logging

from openai import OpenAI

logger = logging.getLogger(__name__)


class OpenAIService:
    def __init__(self, model: str = 'gpt-4o-mini'):
        self.model = model
        self.client = OpenAI()

    def _extract_json(self, text: str) -> str:
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
        kwargs = {
            'model': self.model,
            'messages': [{'role': 'system', 'content': prompt}, {'role': 'user', 'content': text}],
            'temperature': 0.3,
            'max_tokens': 2000,
        }
        if expect_json and 'gpt-4' in self.model:
            kwargs['response_format'] = {'type': 'json_object'}
        for attempt in range(3):
            try:
                response = await asyncio.to_thread(self.client.chat.completions.create, **kwargs)
                content = response.choices[0].message.content
                return self._extract_json(content) if expect_json else content
            except Exception as e:
                error_str = str(e).lower()
                is_retryable = any(k in error_str for k in ['rate_limit', '429', '503', 'timeout', 'server_error'])
                if is_retryable and attempt < 2:
                    wait_time = 2 * (attempt + 1)
                    logger.warning(f'Retryable error, waiting {wait_time}s: {str(e)}')
                    await asyncio.sleep(wait_time)
                    continue
                logger.error(f'OpenAI API error: {str(e)}')
                raise Exception(f'AI service error: {str(e)}')
