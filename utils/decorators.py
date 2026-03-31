from config import types, ADMIN_ID, groups
from typing import Literal, Callable
from functools import wraps


def check_chat_type(allowed_type: Literal["private", "group", "supergroup", "channel"]):
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(message: types.Message, *args, **kwargs):
            if message.chat.type != allowed_type:
                await message.answer(f"Это нельзя использовать в чате \"{message.chat.type}\"")
                return
            return await func(message, *args, **kwargs)
        return wrapper
    return decorator



def check_group():
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(message: types.Message, *args, **kwargs):
            if str(message.text) not in groups:
                await message.answer(f"❌ Извините, я не знаю такую группу \"{str(message.text)}\".\n\n📝 Пожалуйста, проверьте номер группы и попробуйте снова.")
                return
            return await func(message, *args, **kwargs)
        return wrapper
    return decorator    


def if_admin(type: Literal["msg", "call", "user_id"]):
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            if type == "msg":
                message: types.Message = args[0]
                if str(message.from_user.id) != str(ADMIN_ID):
                    return
                return await func(*args, **kwargs)
            elif type == "call":
                call: types.CallbackQuery = args[0]
                if str(call.from_user.id) != str(ADMIN_ID):
                    return
                return await func(*args, **kwargs)
            elif type == "user_id":
                user_id = args[0]
                if str(user_id) != str(ADMIN_ID):
                    return
                return await func(*args, **kwargs)
        return wrapper
    return decorator