import importlib
import os

def load_plugins(plugin_directory):
    plugins = []
    for filename in os.listdir(plugin_directory):
        if filename.endswith('.py'):
            module_name = filename[:-3]  # Remove .py extension
            module = importlib.import_module(f'plugins.{module_name}')
            if hasattr(module, 'Plugin'):
                plugins.append(module.Plugin())
    return plugins
