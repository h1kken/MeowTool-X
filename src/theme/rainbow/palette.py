from __future__ import annotations

from math import cos, pi

from PySide6.QtGui import QColor

from src.theme.colors import to_qcolor
from src.theme.gradients import adjust_qcolor

CLASSIC_RAINBOW_STOPS: tuple[tuple[float, str], ...] = (
    (0.00, '#ff0000'),
    (0.14, '#ff8a00'),
    (0.28, '#fff000'),
    (0.42, '#00ff66'),
    (0.58, '#00d5ff'),
    (0.72, '#4b5cff'),
    (0.86, '#ff00c8'),
    (1.00, '#ff0000'),
)

PASTEL_RAINBOW_STOPS: tuple[tuple[float, str], ...] = (
    (0.00, '#f3a8c8'),
    (0.16, '#f6c79a'),
    (0.32, '#f2efae'),
    (0.48, '#aee9d2'),
    (0.64, '#abd0f5'),
    (0.82, '#d2b6f2'),
    (1.00, '#f3a8c8'),
)

CANDY_RAINBOW_STOPS: tuple[tuple[float, str], ...] = (
    (0.00, '#ff6fae'),
    (0.16, '#ffb36b'),
    (0.32, '#fff27a'),
    (0.48, '#7cf0b8'),
    (0.64, '#7dc9ff'),
    (0.82, '#c28cff'),
    (1.00, '#ff6fae'),
)

RAINBOW_PALETTES: dict[str, tuple[tuple[float, str], ...]] = {
    'Classic': CLASSIC_RAINBOW_STOPS,
    'Pastel': PASTEL_RAINBOW_STOPS,
    'Candy': CANDY_RAINBOW_STOPS,
}


def rainbow_palette_names() -> list[str]:
    return list(RAINBOW_PALETTES.keys())


def resolve_rainbow_stops(
    palette: str | None = None,
    *,
    fallback: str = 'Classic',
) -> tuple[tuple[float, str], ...]:
    if isinstance(palette, str):
        needle = palette.strip().casefold()
        for name, stops in RAINBOW_PALETTES.items():
            if name.casefold() == needle:
                return stops
    return RAINBOW_PALETTES.get(fallback, CLASSIC_RAINBOW_STOPS)


def sample_rainbow_color(
    phase: float,
    *,
    palette: str | None = None,
    stops: tuple[tuple[float, str], ...] | None = None,
    brightness: float = 1.0,
) -> QColor:
    resolved_stops = stops if isinstance(stops, tuple) else resolve_rainbow_stops(palette)
    normalized = float(phase) % 1.0
    previous_offset, previous_color = resolved_stops[0]
    color = to_qcolor(resolved_stops[-1][1]) or QColor()

    for next_offset, next_color in resolved_stops[1:]:
        if normalized <= next_offset:
            span = max(next_offset - previous_offset, 1e-9)
            mix = max(0.0, min(1.0, (normalized - previous_offset) / span))
            start = to_qcolor(previous_color) or QColor()
            end = to_qcolor(next_color) or QColor()
            color = QColor(
                round(start.red() + (end.red() - start.red()) * mix),
                round(start.green() + (end.green() - start.green()) * mix),
                round(start.blue() + (end.blue() - start.blue()) * mix),
                round(start.alpha() + (end.alpha() - start.alpha()) * mix),
            )
            break
        previous_offset, previous_color = next_offset, next_color

    return adjust_qcolor(color, brightness=brightness)


def build_rainbow_gradient_data(
    phase: float,
    *,
    palette: str | None = None,
    stops: tuple[tuple[float, str], ...] | None = None,
    brightness: float = 1.0,
    angle_degrees: float = 0.0,
    span: float = 0.035,
) -> dict[str, object]:
    resolved_stops = stops if isinstance(stops, tuple) else resolve_rainbow_stops(palette)
    normalized_phase = float(phase) % 1.0
    phase_span = max(0.0, min(float(span), 0.08))
    gradient_phases = (
        (0.00, (normalized_phase - phase_span) % 1.0, 0),
        (0.34, (normalized_phase - phase_span) % 1.0, 0),
        (0.42, (normalized_phase - phase_span * 0.55) % 1.0, 48),
        (0.47, (normalized_phase - phase_span * 0.22) % 1.0, 140),
        (0.50, normalized_phase, 255),
        (0.53, (normalized_phase + phase_span * 0.22) % 1.0, 140),
        (0.58, (normalized_phase + phase_span * 0.55) % 1.0, 48),
        (0.66, (normalized_phase + phase_span) % 1.0, 0),
        (1.00, (normalized_phase + phase_span) % 1.0, 0),
    )
    shifted: list[list[object]] = []

    for pos, sample_phase, alpha in gradient_phases:
        color = sample_rainbow_color(
            sample_phase,
            palette=palette,
            stops=resolved_stops,
            brightness=brightness,
        )
        color.setAlpha(int(alpha))
        shifted.append([float(pos), color.name(QColor.NameFormat.HexArgb)])

    return {
        'type': 'linear',
        'angle': float(angle_degrees),
        'stops': shifted,
    }


def rainbow_gradient_angle(phase: float, *, wobble_degrees: float = 5.0) -> float:
    normalized = float(phase) % 1.0
    base = normalized * 360.0
    wobble = float(wobble_degrees) * cos(normalized * 2.0 * pi)
    return base + wobble
