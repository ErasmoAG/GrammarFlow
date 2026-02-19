# game/difficulty.py

from dataclasses import dataclass


@dataclass(frozen=True)
class DifficultySettings:
    """
    Configuración de cada dificultad.
    """
    fall_speed_multiplier: float
    select_box_scale: float


# Configuración de dificultades
DIFFICULTY_SETTINGS = {
    "Easy": DifficultySettings(
        fall_speed_multiplier=1.00,
        select_box_scale=1.00
    ),

    "Normal": DifficultySettings(
        fall_speed_multiplier=1.01,   # +1% velocidad
        select_box_scale=0.90         # caja un poco más pequeña
    ),

    "Hard": DifficultySettings(
        fall_speed_multiplier=1.00,
        select_box_scale=1.00
    ),
}


def get_difficulty_settings(difficulty_name: str) -> DifficultySettings:
    """
    Devuelve la configuración correspondiente a la dificultad seleccionada.
    Si no encuentra la dificultad, devuelve Easy por defecto.
    """
    return DIFFICULTY_SETTINGS.get(
        difficulty_name,
        DIFFICULTY_SETTINGS["Easy"]
    )
