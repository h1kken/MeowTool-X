- Do something with object names...

- Recreate Popup

- Fix: widgets/common/combo_box.py
- Rewrite: widgets/settings/roblox/cookie_checker/cookie_checker.py

- Coded default icons for buttons
- Smart pick path (like icons, where we firstly search in user path then fallback to src if errors)

- History block

- Translations Schema:
    1. We have translates: en, ru, ch, etc.
    2. User translates don't have any translations - append it from ENGLISH with # at the KEY start
        2.1. Translation file should be created from 0 with a certain order
    3. User translates overwrite our - don't touch
