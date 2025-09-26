def validate_config(user_config: dict, default_config: dict) -> dict:
    validated_config = {}
    
    for key, default_value in default_config.items():
        if key in user_config:
            user_value = user_config[key]
            if isinstance(default_value, dict):
                validated_config[key] = validate_config(user_value, default_value)
            elif type(user_value) is str:
                if user_value.strip().lower() in ('1', 'true', 'yes'):
                    validated_config[key] = True
                elif user_value.strip().lower() in ('0', 'false', 'no'):
                    validated_config[key] = False
                else:
                    validated_config[key] = user_value
            elif type(default_value) is tuple:
                if type(user_value) is not int and str(user_value).isdigit():
                    user_value = int(user_value)
                    if default_value[1] <= user_value <= default_value[2]:
                        validated_config[key] = user_value
                    else:
                        validated_config[key] = default_config[0]
            elif type(user_value) is not type(default_value):
                validated_config[key] = default_value
            else:
                validated_config[key] = user_value
                
    return validated_config