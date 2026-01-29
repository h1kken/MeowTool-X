from typing import Any, Callable
from PySide6.QtCore import QObject, QEvent, QAbstractAnimation, QParallelAnimationGroup
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QWidget
from src.utils.consts import EVENT_ACTIONS, GRADIENT_DIRECTIONS


def _l(s: float, e: float, t: float) -> int:
    return int(s + (e - s) * t)


def _interpolate_color(s: QColor, e: QColor, t: float) -> QColor:
    return QColor(
        _l(s.red(),   e.red(),   t),
        _l(s.green(), e.green(), t),
        _l(s.blue(),  e.blue(),  t),
        _l(s.alpha(), e.alpha(), t),
    )


class TimerAnimation(QAbstractAnimation):
    def __init__(self, duration: int, update_fn: Callable[[float], None], parent=None):
        super().__init__(parent)
        self._duration = duration
        self._update_fn = update_fn

    def duration(self) -> int:
        return self._duration

    def updateCurrentTime(self, msec: int) -> None:
        t = min(msec / self._duration, 1.0)
        self._update_fn(t)


class AnimationManager(QObject):
    def __init__(self, root: QWidget):
        super().__init__()
        self._root = root
        self._animations: dict[QWidget, dict[str, QParallelAnimationGroup]] = {}
        self._cache: dict[QWidget, dict[str, Any]] = {}

    def load(self, animations: dict[str, dict[str, dict]]):
        for anim_groups in self._animations.values():
            for anim_group in anim_groups.values():
                anim_group.stop()
        
        self._animations.clear()
        self._cache.clear()

        for obj_name, anim_datas in animations.items():
            widget: QWidget = self._root.findChild(QWidget, obj_name)
            if not widget:
                continue

            widget.installEventFilter(self)
            self._animations[widget] = {}
            self._cache[widget] = {}
            
            action_groups: dict[str, QParallelAnimationGroup] = {}
            
            for anim_data in anim_datas.values():
                action = anim_data.get('action')
                
                if not action:
                    continue
                
                anim_group = action_groups.setdefault(action, QParallelAnimationGroup(widget))
                self._build_animation(widget, anim_data, anim_group)
            
            for action, anim_group in action_groups.items():
                self._animations[widget][action] = anim_group

    def _build_animation(self, widget: QWidget, anim: dict, group: QParallelAnimationGroup):
        property = anim.get('property')
        match property:
            case 'background':
                group.addAnimation(
                    TimerAnimation(
                        duration=anim.get('duration', 300),
                        update_fn=lambda t, w=widget, a=anim: self._animate_color(w, a, t),
                        parent=widget
                    )
                )
            case 'gradient':
                group.addAnimation(
                    TimerAnimation(
                        duration=anim.get('duration', 300),
                        update_fn=lambda t, w=widget, a=anim: self._animate_gradient(w, a, t),
                        parent=widget
                    )
                )
            # TODO: добавить geometry и другие свойства

    def eventFilter(self, obj: QObject, event: QEvent):
        if obj not in self._animations:
            return super().eventFilter(obj, event)
        
        action = EVENT_ACTIONS.get(event.type())
        if action:
            self._play(obj, action)
        
        return super().eventFilter(obj, event)

    def _play(self, widget: QWidget, action: str):
        group: QParallelAnimationGroup = self._animations.get(widget, {}).get(action)
        if not group:
            return

        for i in range(group.animationCount()):
            anim = group.animationAt(i)
            if hasattr(anim, 'anim'):
                anim.anim.pop('from', None)

        group.stop()
        group.start()

    def _animate_color(self, widget: QWidget, anim: dict, t: float):
        cache = self._cache.setdefault(widget, {})

        if 'from' not in anim:
            anim['from'] = cache.get('background', QColor(anim.get('start', '#000000')))

        start: QColor = anim['from']
        end: QColor = QColor(anim.get('end', '#000000'))

        color = _interpolate_color(start, end, t)

        widget.setStyleSheet(f'background-color: {color.name(QColor.NameFormat.HexArgb)};')

        cache['background'] = color


    def _animate_gradient(self, widget: QWidget, anim: dict, t: float):
        cache = self._cache.setdefault(widget, {})

        if 'from' not in anim:
            start = cache.get('gradient', {
                'direction': anim.get('direction', 'vertical'),
                'stops': [
                    {
                        'pos': s['pos'],
                        'color': QColor(s['color'])
                    } for s in anim.get('start', [])
                ]
            })
            anim['from'] = start

        start_grad = anim['from']
        end_grad = {
            'direction': anim.get('direction', start_grad['direction']),
            'stops': [
                {
                    'pos': s['pos'],
                    'color': QColor(e['color'])
                } for s, e in zip(start_grad['stops'], anim.get('end', []))
            ]
        }

        new_stops = []
        for s, e in zip(start_grad['stops'], end_grad['stops']):
            color = _interpolate_color(s['color'], e['color'], t)
            new_stops.append({'pos': s['pos'], 'color': color})

        new_grad = {'direction': end_grad['direction'], 'stops': new_stops}

        self._apply_gradient(widget, new_grad)

        cache['gradient'] = new_grad


    def _apply_gradient(self, widget: QWidget, grad: dict):
        dir = grad['direction']
        x1, y1, x2, y2 = GRADIENT_DIRECTIONS.get(dir, (0, 0, 0, 1))

        parts = [
            f"stop:{s['pos']} {s['color'].name(QColor.NameFormat.HexArgb)}"
            for s in grad['stops']
        ]

        style = f'''
            background-color: qlineargradient(
                x1:{x1}, y1:{y1},
                x2:{x2}, y2:{y2},
                {', '.join(parts)}
            );
        '''

        widget.setStyleSheet(style)

