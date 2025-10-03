import openai
from abc import ABC, abstractmethod
from typing import List, Dict, Union


class LLMProvider(ABC):
    """
    Abstract base class for LLM providers.
    """

    @abstractmethod
    def __init__(self, api_key: str, base_url: str = None):
        pass

    @abstractmethod
    def generate_response(self, prompt: Union[str, List[Dict[str, str]]], **kwargs):
        pass


class OpenAIProvider(LLMProvider):
    """
    OpenAI provider implementation.
    """

    def __init__(self, api_key: str, base_url: str = None, model: str = None):
        if model is None:
            raise ValueError("model parameter is required")
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        if base_url:
            self.client = openai.OpenAI(api_key=self.api_key, base_url=self.base_url)
        else:
            self.client = openai.OpenAI(api_key=self.api_key)

    def generate_response(self, prompt: Union[str, List[Dict[str, str]]], **kwargs):
        # Support both old string format and new messages format
        if isinstance(prompt, str):
            messages = [{"role": "user", "content": prompt}]
        else:
            messages = prompt

        completion = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
        )
        return completion.choices[0].message.content


class LLM:
    """
    LLM class for interacting with different LLM providers.
    """

    def __init__(self, provider: LLMProvider):
        self.provider = provider

    def generate_response(self, prompt: Union[str, List[Dict[str, str]]], **kwargs):
        return self.provider.generate_response(prompt, **kwargs)
