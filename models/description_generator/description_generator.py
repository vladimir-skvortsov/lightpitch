from typing import Optional
from pydantic import BaseModel, Field
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain.output_parsers import RetryOutputParser
from langchain_core.runnables import RunnableLambda, RunnableParallel

from ..utils.OpenRouter import OpenRouter
from ..utils.JsonExtractor import JsonExtractor


class DocumentGradeSchema(BaseModel):
    description: str = Field(description='Description of the pitch in Russian')


template = """
You are an expert at creating compelling descriptions for presentations and pitches.
Your task is to create a concise but informative description of a presentation based on the provided information.

The description should:
- Be concise (2-3 sentences, maximum 150 words)
- Capture the essence and key points of the presentation
- Be engaging for the audience
- Use professional but accessible language
- Highlight value and practical benefits
- Be written in Russian language (output in Russian)

If only a title is provided, make reasonable assumptions about the content based on the topic.

Title: {title}

Speech content:
{speech_text}

Presentation content:
{presentation_text}

{format_instructions}
"""

parser = PydanticOutputParser(pydantic_object=DocumentGradeSchema)

prompt = PromptTemplate(
    template=template,
    input_variables=['document', 'query'],
    partial_variables={'format_instructions': parser.get_format_instructions()},
)


class DescriptionGenerator:
    def __init__(self, model_name: str = 'openai/gpt-5-nano'):
        self.model_name = model_name
        self.llm = OpenRouter(model=model_name, temperature=0.7, max_tokens=300)
        self.retry_parser = RetryOutputParser.from_llm(
            parser=parser,
            llm=self.llm,
            max_retries=3,
        )

        self.chain = RunnableParallel(
            completion=prompt | self.llm | StrOutputParser() | JsonExtractor(), prompt_value=prompt
        ) | RunnableLambda(lambda x: self.retry_parser.parse_with_prompt(**x))

    def _generate_fallback_description(
        self,
        title: str,
        speech_text: Optional[str] = None,
        presentation_text: Optional[str] = None,
    ) -> str:
        base_description = f"Презентация на тему '{title}'"

        if speech_text:
            word_count = len(speech_text.split())
            if word_count < 50:
                base_description += ' с кратким обзором ключевых идей'
            elif word_count < 200:
                base_description += ' с детальным разбором темы и практическими примерами'
            else:
                base_description += ' с глубоким анализом и множеством примеров'

        if presentation_text:
            base_description += '. Включает презентационные материалы для лучшего понимания темы'

        base_description += '.'

        return base_description

    def generate_description(
        self, title: str, speech_text: Optional[str] = None, presentation_text: Optional[str] = None
    ) -> str:
        try:
            return self.chain.invoke(
                {
                    'title': title,
                    'speech_text': speech_text[:1000] if speech_text else 'Not provided',
                    'presentation_text': presentation_text[:1000] if presentation_text else 'Not provided',
                }
            ).description
        except Exception:
            return self._generate_fallback_description(title, speech_text, presentation_text)
