# Copyright (c) 2025 Cafesuada
# All rights reserved.

from typing import Annotated
from semantic_kernel.functions import kernel_function


class LightsPlugin:
    lights = [
        {'id': 1, 'name': 'Table Lamp', 'is_on': False},
        {'id': 2, 'name': 'Porch light', 'is_on': False},
        {'id': 3, 'name': 'Chandelier', 'is_on': True},
    ]

    @kernel_function(
        name='get_lights',
        description='Gets a list of lights and their current state',
    )
    def get_state(
        self,
    ) -> list[dict[str, int | str | bool]]:
        """Gets a list of lights and their current state."""
        return self.lights

    @kernel_function(
        name='change_state',
        description='Changes the state of the light',
    )
    def change_state(
        self,
        _id: int,
        is_on: bool,
    ) -> dict[str, int | str | bool] | None:
        """Changes the state of the light."""
        for light in self.lights:
            if light['id'] == _id:
                light['is_on'] = is_on
                return light
        return None
