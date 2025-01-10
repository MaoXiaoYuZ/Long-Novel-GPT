from llm_api import ModelConfig

def get_model_config_from_provider_model(provider_model):
    from config import API_SETTINGS
    provider, model = provider_model.split('/')
    provider_config = API_SETTINGS[provider]
    
    if provider == 'doubao':
        # Get the index of the model in available_models to find corresponding endpoint_id
        model_index = provider_config['available_models'].index(model)
        endpoint_id = provider_config['endpoint_ids'][model_index] if model_index < len(provider_config['endpoint_ids']) else ''
        model_config = {**provider_config, 'model': model, 'endpoint_id': endpoint_id}
    else:
        model_config = {**provider_config, 'model': model}
    
    # Remove lists from config before creating ModelConfig
    if 'available_models' in model_config:
        del model_config['available_models']
    if 'endpoint_ids' in model_config:
        del model_config['endpoint_ids']

    return ModelConfig(**model_config)