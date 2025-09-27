def parse_config(text: str) -> dict:
    parsed_config = {}
    stack = [(parsed_config, -1)]

    for line in text.splitlines():
        if not line.strip():
            continue

        indent = len(line) - len(line.lstrip('\t'))
        line = line.strip()
        
        if ':' in line:
            key, value = map(str.strip, line.split(':', 1))
            stack[-1][0][key] = value
        else:
            while stack and stack[-1][1] >= indent:
                stack.pop()
            new_dict = {}
            stack[-1][0][line] = new_dict
            stack.append((new_dict, indent))
            
    return parsed_config

def validate_config(user_config: dict, default_config: dict, *, recovery_missing: bool = False) -> dict:
    validated_config = {}
    
    for key, default_value in default_config.items():
        if key in user_config:
            validated_config[key] = convert_value(user_config[key], default_value)
        else:
            if recovery_missing:
                validated_config[key] = default_value
                
    return validated_config

def convert_value(user_value, default_value):
    if isinstance(default_value, dict):
        return validate_config(user_value, default_value)
    elif isinstance(default_value, tuple) and len(default_value) == 3:
        for await_type in (int, float):
            if isinstance(default_value[0], await_type):
                try:
                    user_value = await_type(user_value)
                    if default_value[1] <= user_value <= default_value[2]:
                        return user_value
                    else:
                        return default_value[0]
                except ValueError:
                    return default_value[0]
    elif isinstance(default_value, int):
        try:
            return int(user_value)
        except ValueError:
            return default_value
    elif isinstance(user_value, str):
        low = user_value.strip().lower()
        if low in ('1', 'true', 'yes', '+'):
            return True
        elif low in ('0', 'false', 'no', '-'):
            return False
        else:
            return user_value
    elif type(user_value) is not type(default_value):
        return default_value
    else:
        return user_value