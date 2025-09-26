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
    elif isinstance(user_value, str):
        user_value = user_value.strip().lower()
        if user_value in ('1', 'true', 'yes', '+'):
            return True
        elif user_value in ('0', 'false', 'no', '-'):
            return False
        else:
            return user_value
    elif isinstance(default_value, tuple):
        if type(user_value) is not int and str(user_value).isdigit():
            user_value = int(user_value)
            if default_value[1] <= user_value <= default_value[2]:
                return user_value
            else:
                return default_value[0]
    elif type(user_value) is not type(default_value):
        return default_value
    else:
        return user_value