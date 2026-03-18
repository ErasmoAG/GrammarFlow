# game/difficulty.py

from dataclasses import dataclass


@dataclass(frozen=True)
class DifficultySettings:
    """
    Configuración completa de cada dificultad.
    Este archivo es la ÚNICA fuente de verdad para los parámetros de dificultad.
    """
    fall_speed_multiplier: float   # multiplicador sobre BASE_FALL_SPEED
    hitbox_scale: float            # escala sobre HITBOX_HEIGHT base
    lives: int                     # vidas iniciales


# ─── Configuración de dificultades ───────────────────────────────────────────
DIFFICULTY_SETTINGS = {
    "facil": DifficultySettings(
        fall_speed_multiplier=1.00,   # velocidad base
        hitbox_scale=1.00,            # hitbox completa
        lives=6,
    ),
    "normal": DifficultySettings(
        fall_speed_multiplier=1.70,   # +70% más rápido
        hitbox_scale=0.75,            # 25% más pequeña
        lives=4,
    ),
    "dificil": DifficultySettings(
        fall_speed_multiplier=2.40,   # +140% más rápido
        hitbox_scale=0.55,            # 45% más pequeña
        lives=3,
    ),
}


def get_difficulty_settings(difficulty_id: str) -> DifficultySettings:
    """
    Devuelve la configuración para el ID de dificultad dado (facil/normal/dificil).
    Si no existe, retorna Fácil por defecto.
    """
    return DIFFICULTY_SETTINGS.get(difficulty_id, DIFFICULTY_SETTINGS["facil"])