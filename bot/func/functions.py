import logging
import os
import aiohttp
import json
from aiogram import types
from asyncio import Lock
from functools import wraps
from dotenv import load_dotenv

# --- Environment
load_dotenv()
# --- Environment Checker
token = os.getenv("TOKEN")
admin_ids = list(map(int, os.getenv("ADMIN_IDS", "").split(",")))
ollama_base_url = os.getenv("OLLAMA_BASE_URL")
ollama_port = os.getenv("OLLAMA_PORT", "11434")
log_level_str = os.getenv("LOG_LEVEL", "INFO")

# --- Other
log_levels = list(logging._levelToName.values())

# Set default level to be INFO
if log_level_str not in log_levels:
    log_level = logging.DEBUG
else:
    log_level = logging.getLevelName(log_level_str)

logging.basicConfig(level=log_level)

# Ollama API
async def model_list():
    async with aiohttp.ClientSession() as session:
        url = f"http://{ollama_base_url}:{ollama_port}/api/tags"
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                return data["models"]
            else:
                return []

async def generate(payload: dict, modelname: str, prompt: str):
    async with aiohttp.ClientSession() as session:
        url = f"http://{ollama_base_url}:{ollama_port}/api/chat"
        async with session.post(url, json=payload) as response:
            async for chunk in response.content:
                if chunk:
                    decoded_chunk = chunk.decode()
                    if decoded_chunk.strip():
                        yield json.loads(decoded_chunk)

# Aiogram functions & wraps
def perms_admins(func):
    @wraps(func)
    async def wrapper(message: types.Message = None, query: types.CallbackQuery = None):
        user_id = message.from_user.id if message else query.from_user.id
        if user_id in admin_ids:
            if message:
                return await func(message)
            elif query:
                return await func(query=query)
        else:
            response_text = "Access Denied: This command is reserved for administrators."
            if message:
                await message.answer(response_text)
            elif query:
                await query.answer(response_text)
            logging.info(f"Unauthorized access attempt by {user_id}")
    return wrapper

# Open access function decorator
def open_access(func):
    @wraps(func)
    async def wrapper(message: types.Message = None, query: types.CallbackQuery = None):
        if message:
            return await func(message)
        elif query:
            return await func(query=query)
    return wrapper

# Context-Related
class contextLock:
    lock = Lock()

    async def __aenter__(self):
        await self.lock.acquire()

    async def __aexit__(self, exc_type, exc_value, exc_traceback):
        self.lock.release()
