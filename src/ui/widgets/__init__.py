from src.ui.widgets.main.checkables import MTSwitch
from src.ui.widgets.main.containers import (
    MTComboBox,
    MTDropZone,
    MTButtonGroup,
    MTLabeledList,
    MTListWidget,
    MTScrollArea,
    MTWidget,
)
from src.ui.widgets.main.inputs import (
    MTDoubleSpinBox,
    MTLineEdit,
    MTSlider,
    MTSpinBox,
)
from src.ui.widgets.main.media import (
    MTAudioOutput,
    MTMediaPlayer,
    MTMediaWidget,
    MTVideoWidget,
    SidebarMediaWidget,
)
from src.ui.widgets.main.popups import MTPopup
from src.ui.widgets.main.stacks import MTInlineEditorStack
from src.ui.widgets.main.text import MTButton, MTLabel, MTPlainLabel

# settings
from src.ui.widgets.settings.buttons import MTButtonSetting
from src.ui.widgets.settings.checkables import MTCheckBoxSetting, MTSwitchSetting, MTSwitchRowSetting
from src.ui.widgets.settings.containers import MTColumnsSetting, MTCollapsibleContainer, MTComboBoxSetting
from src.ui.widgets.settings.inputs import MTTextSetting, MTPathSetting, MTSliderSetting

__all__ = [
    # main
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
    'MTComboBox',
    'MTScrollArea',
    'MTWidget',
    'MTLabeledList',
    'MTListWidget',
    'MTDropZone',
    'MTButtonGroup',
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
