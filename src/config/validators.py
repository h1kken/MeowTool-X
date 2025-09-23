def validate_config(user_config: dict, default_config: dict) -> dict:
    validated_config = {}
    
    for key, default_value in default_config.items():
        if key in user_config:
            user_value = user_config[key]
            if isinstance(default_value, dict):
                validated_config[key] = validate_config(user_value, default_value)
            elif type(user_value) is not type(default_value):
                validated_config[key] = default_value
            else:
                validated_config[key] = user_value
                
    return validated_config