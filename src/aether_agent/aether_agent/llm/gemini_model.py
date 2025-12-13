# Copyright (c) 2025 Cafesuada
# All rights reserved.

import asyncio
from typing import override

from rclpy.impl.rcutils_logger import RcutilsLogger
from semantic_kernel.connectors.ai.function_choice_behavior import (
    FunctionChoiceBehavior,
)
from semantic_kernel.connectors.ai.google.google_ai import (
    GoogleAIChatCompletion,
    GoogleAIPromptExecutionSettings,
)
from semantic_kernel.functions import KernelArguments

from .large_language_model import LargeLanguageModel


class GeminiModel(LargeLanguageModel):
    """LLM implementation using Gemini."""

    def __init__(
        self,
        api_key: str,
        gemini_model_id: str = 'gemini-2.5-flash',
        *,
        logger: RcutilsLogger | None = None,
    ) -> None:
        super().__init__()

        self.__chat_completion_service = GoogleAIChatCompletion(
            api_key=api_key,
            gemini_model_id=gemini_model_id,
        )

        self.kernel.add_service(self.__chat_completion_service)

        self.__execution_settings = GoogleAIPromptExecutionSettings()
        self.__execution_settings.function_choice_behavior = (
            FunctionChoiceBehavior.Auto()  # pyright: ignore
        )

        self.__kernel_arguments = KernelArguments()
        self.__logger = logger

    @override
    def infer(self, prompt: str) -> str:
        self._history.add_user_message(prompt)
        response = 'Failed to generate response'
        try:
            corou = self.__chat_completion_service.get_chat_message_content(
                chat_history=self._history,
                settings=self.__execution_settings,
                kernel=self.kernel,
                arguments=self.__kernel_arguments,
            )
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(corou)
            loop.close()

            if result is not None:
                self._history.add_message(result)
                response = str(result)
        except Exception as e:
            if self.__logger:
                self.__logger.error(f'LLM infer exception: {str(e)}') # pyright: ignore
            response = 'An error occured while processing your request'

        return response
