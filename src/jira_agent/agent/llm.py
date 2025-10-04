import openai
import boto3
import json
from abc import ABC, abstractmethod
from typing import List, Dict, Union, Optional


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


class BedrockProvider(LLMProvider):
    """
    AWS Bedrock provider implementation.
    Supports Anthropic Claude models via the AWS Bedrock runtime API.
    Requires an inference profile (system-defined or custom ARN).
    """

    def __init__(
        self,
        region: str,
        inference_profile: str,
        access_key_id: Optional[str] = None,
        secret_access_key: Optional[str] = None,
    ):
        if not inference_profile:
            raise ValueError("inference_profile parameter is required")

        self.inference_profile = inference_profile

        # Initialize boto3 client with explicit credentials if provided
        # Otherwise, boto3 will use default credential chain (env vars, ~/.aws/credentials, IAM role)
        client_kwargs = {
            "service_name": "bedrock-runtime",
            "region_name": region,
        }

        if access_key_id and secret_access_key:
            client_kwargs["aws_access_key_id"] = access_key_id
            client_kwargs["aws_secret_access_key"] = secret_access_key

        self.client = boto3.client(**client_kwargs)

    def generate_response(self, prompt: Union[str, List[Dict[str, str]]], **kwargs):
        # Support both old string format and new messages format
        if isinstance(prompt, str):
            messages = [{"role": "user", "content": prompt}]
        else:
            messages = prompt

        # Extract system message if present (Bedrock requires it as separate parameter)
        system_prompt = None
        filtered_messages = []
        for msg in messages:
            if msg.get("role") == "system":
                # Combine multiple system messages if present
                if system_prompt is None:
                    system_prompt = msg.get("content", "")
                else:
                    system_prompt += "\n\n" + msg.get("content", "")
            else:
                filtered_messages.append(msg)

        # For Claude models on Bedrock, use the Messages API format
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "messages": filtered_messages,
            "max_tokens": kwargs.get("max_tokens", 4096),
            "temperature": kwargs.get("temperature", 0.7),
        }

        # Add system prompt if present
        if system_prompt:
            body["system"] = system_prompt

        # Invoke the model using the inference profile
        response = self.client.invoke_model(
            modelId=self.inference_profile,
            body=json.dumps(body),
            accept="application/json",
            contentType="application/json",
        )

        # Parse response
        response_body = json.loads(response["body"].read())

        # Extract the generated text from Claude's response format
        return response_body["content"][0]["text"]


class LLM:
    """
    LLM class for interacting with different LLM providers.
    """

    def __init__(self, provider: LLMProvider):
        self.provider = provider

    def generate_response(self, prompt: Union[str, List[Dict[str, str]]], **kwargs):
        return self.provider.generate_response(prompt, **kwargs)
