"""Система плагинов JARVIS - модульная архитектура действий."""
import os
import importlib.util
from typing import Dict, List, Callable, Any
from functools import wraps


# Реестр всех зарегистрированных плагинов
_plugin_registry: Dict[str, Dict[str, Any]] = {}


def jarvis_action(name: str, description: str = ""):
    """Декоратор для регистрации действия плагина."""
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        
        # Регистрируем действие
        if name not in _plugin_registry:
            _plugin_registry[name] = {
                "description": description,
                "function": wrapper,
                "params": []
            }
        else:
            _plugin_registry[name]["function"] = wrapper
            if description:
                _plugin_registry[name]["description"] = description
        
        return wrapper
    return decorator


def register_plugin(plugin_name: str, version: str = "1.0"):
    """Декоратор для регистрации плагина."""
    def decorator(cls):
        _plugin_registry[f"_plugin_{plugin_name}"] = {
            "type": "plugin",
            "name": plugin_name,
            "version": version,
            "class": cls
        }
        return cls
    return decorator


def load_plugins_from_dir(plugin_dir: str = "plugins") -> Dict[str, Dict[str, Any]]:
    """Загружает все плагины из директории."""
    if not os.path.exists(plugin_dir):
        os.makedirs(plugin_dir)
        return _plugin_registry
    
    for filename in os.listdir(plugin_dir):
        if filename.endswith(".py") and not filename.startswith("_"):
            module_name = filename[:-3]
            module_path = os.path.join(plugin_dir, filename)
            
            try:
                spec = importlib.util.spec_from_file_location(module_name, module_path)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
            except Exception as e:
                print(f"[ПЛАГИНЫ] Ошибка загрузки {filename}: {e}")
    
    return _plugin_registry


def get_action(name: str) -> Callable | None:
    """Возвращает функцию действия по имени."""
    plugin = _plugin_registry.get(name)
    if plugin and "function" in plugin:
        return plugin["function"]
    return None


def get_all_actions() -> Dict[str, str]:
    """Возвращает все действия с описаниями для генерации промпта."""
    actions = {}
    for name, data in _plugin_registry.items():
        if not name.startswith("_plugin_") and "function" in data:
            actions[name] = data.get("description", "")
    return actions


def generate_prompt_section() -> str:
    """Генерирует секцию системного промпта с описанием действий."""
    actions = get_all_actions()
    if not actions:
        return ""
    
    prompt = "\nДОПОЛНИТЕЛЬНЫЕ ДЕЙСТВИЯ ПЛАГИНОВ:\n"
    for name, desc in actions.items():
        prompt += f'{{"action": "{name}"}} — {desc}\n'
    return prompt


# Инициализация плагинов при импорте
def init_plugins(plugin_dir: str = "plugins"):
    """Инициализирует систему плагинов."""
    return load_plugins_from_dir(plugin_dir)
