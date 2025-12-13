# Copyright (c) 2025 Cafesuada
# All rights reserved.

"""This module contains base Large Language Model implementation."""
from abc import ABC, abstractmethod

from semantic_kernel import Kernel
from semantic_kernel.contents.chat_history import ChatHistory


class LargeLanguageModel(ABC):
    """Large language model base class.

    This class is designed to integrate with Semantic Kernel.
    """

    def __init__(self) -> None:
        """Base initialization."""
        self.__kernel = Kernel()
        self._history = ChatHistory()

    @abstractmethod
    def infer(self, prompt: str) -> str:
        """Request LLM response from user prompt."""
        raise NotImplementedError

    @property
    def kernel(self) -> Kernel:
        """Model's internel kernel."""
        return self.__kernel
