# default
from src.ui.widgets.checkables import MTSwitch
from src.ui.widgets.containers import (
    MTComboBox,
    MTDropZone,
    MTLabeledList,
    MTListWidget,
    MTRadioButton,
    MTScrollArea,
    MTWidget,
)
from src.ui.widgets.inputs import (
    MTDoubleSpinBox,
    MTLineEdit,
    MTSlider,
    MTSpinBox,
)
from src.ui.widgets.media import (
    MTAudioOutput,
    MTMediaPlayer,
    MTMediaWidget,
    MTVideoWidget,
    SidebarMediaWidget,
)
from src.ui.widgets.popups import MTPopup
from src.ui.widgets.stacks import MTInlineEditorStack
from src.ui.widgets.text import MTButton, MTLabel, MTPlainLabel
# settings
from src.ui.widgets.settings.buttons import MTButtonSetting
from src.ui.widgets.settings.checkables import MTCheckBoxSetting, MTSwitchSetting, MTSwitchRowSetting
from src.ui.widgets.settings.containers import MTColumnsSetting, MTCollapsibleContainer, MTComboBoxSetting
from src.ui.widgets.settings.inputs import MTTextSetting, MTPathSetting, MTSliderSetting

__all__ = [
    # default
    'MTLabel',
    'MTPlainLabel',
    'MTButton',
    'MTSwitch',
    'MTSlider',
    'MTLineEdit',
    'MTSpinBox',
    'MTDoubleSpinBox',
    'MTAudioOutput',
    'MTMediaPlayer',
    'MTMediaWidget',
    'MTVideoWidget',
    'SidebarMediaWidget',
    'MTRadioButton',
    'MTComboBox',
    'MTScrollArea',
    'MTWidget',
    'MTLabeledList',
    'MTListWidget',
    'MTDropZone',
    'MTPopup',
    'MTInlineEditorStack',
    # settings
    'MTButtonSetting',
    'MTCheckBoxSetting',
    'MTSwitchSetting',
    'MTSwitchRowSetting',
    'MTColumnsSetting',
    'MTCollapsibleContainer',
    'MTComboBoxSetting',
    'MTTextSetting',
    'MTPathSetting',
    'MTSliderSetting',
]
