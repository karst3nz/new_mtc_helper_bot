import os
import signal
from config import API_HASH, API_ID, asyncio, create_logger
import subprocess

logger = create_logger(__name__)

# Глобальная переменная для хранения процесса API сервера
api_server_process = None

async def run():
    """Запуск telegram-bot-api сервера в фоновом режиме"""
    global api_server_process
    
    abs_path = os.path.abspath('./custom_bot_api/telegram-bot-api/bin/telegram-bot-api')
    
    # Проверяем существование файла
    if not os.path.isfile(abs_path):
        logger.error(f"Файл telegram-bot-api не найден: {abs_path}")
        return None
    
    cmd = [
        "sudo",
        abs_path,
        f"--api-id={API_ID}",
        f"--api-hash={API_HASH}",
        "--local",  # Включаем локальный режим для дополнительных возможностей
        "--http-port=8081"  # Явно указываем порт
    ]
    
    try:
        logger.info("Запуск telegram-bot-api сервера...")
        
        # Запускаем процесс в фоне (без ожидания завершения)
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            # Не используем communicate(), чтобы процесс работал в фоне
        )
        
        # Сохраняем ссылку на процесс
        api_server_process = process
        
        logger.info(f"telegram-bot-api запущен с PID: {process.pid}")
        
        # Мониторим процесс в фоне
        asyncio.create_task(monitor_process(process))
        
        return process
        
    except Exception as e:
        logger.error(f"Не удалось запустить telegram-bot-api: {e}")
        return None


async def monitor_process(process):
    """Мониторинг процесса telegram-bot-api"""
    try:
        # Читаем stdout и stderr в фоне
        async def read_output(stream, stream_name):
            try:
                while True:
                    line = await stream.readline()
                    if not line:
                        break
                    line_str = line.decode('utf-8', errors='ignore').strip()
                    if line_str:
                        if stream_name == "stderr":
                            logger.error(f"[telegram-bot-api stderr] {line_str}")
                        else:
                            logger.debug(f"[telegram-bot-api stdout] {line_str}")
            except Exception as e:
                logger.warning(f"Ошибка чтения {stream_name}: {e}")
        
        # Запускаем чтение stdout и stderr параллельно
        await asyncio.gather(
            read_output(process.stdout, "stdout"),
            read_output(process.stderr, "stderr"),
            wait_for_process(process)
        )
    except Exception as e:
        logger.error(f"Ошибка мониторинга процесса: {e}")


async def wait_for_process(process):
    """Ожидание завершения процесса"""
    try:
        return_code = await process.wait()
        if return_code != 0:
            logger.error(f"telegram-bot-api завершился с кодом: {return_code}")
        else:
            logger.info("telegram-bot-api завершился нормально")
    except Exception as e:
        logger.error(f"Ошибка ожидания процесса: {e}")


async def shutdown_api_server():
    """Корректное завершение API сервера"""
    global api_server_process
    
    if api_server_process is None:
        logger.info("API сервер не запущен, завершать нечего")
        return
    
    try:
        # Проверяем, что процесс еще работает
        if api_server_process.returncode is not None:
            logger.info(f"API сервер уже завершен (код возврата: {api_server_process.returncode})")
            api_server_process = None
            return
        
        logger.info(f"Завершение telegram-bot-api (PID: {api_server_process.pid})...")
        
        # Отправляем SIGTERM для корректного завершения
        try:
            api_server_process.terminate()
            
            # Ждем завершения до 5 секунд
            try:
                await asyncio.wait_for(api_server_process.wait(), timeout=5.0)
                logger.info("telegram-bot-api корректно завершен")
            except asyncio.TimeoutError:
                # Если не завершился за 5 секунд, принудительно завершаем
                logger.warning("telegram-bot-api не завершился за 5 секунд, принудительное завершение...")
                try:
                    api_server_process.kill()
                    await api_server_process.wait()
                    logger.info("telegram-bot-api принудительно завершен")
                except ProcessLookupError:
                    logger.warning("Процесс уже завершен")
        except ProcessLookupError:
            logger.warning("Процесс telegram-bot-api уже завершен")
        except Exception as e:
            logger.error(f"Ошибка при завершении telegram-bot-api: {e}")
            # Пытаемся принудительно завершить
            try:
                if api_server_process.returncode is None:
                    api_server_process.kill()
                    await api_server_process.wait()
            except Exception:
                pass
        
        api_server_process = None
        
    except Exception as e:
        logger.error(f"Критическая ошибка при завершении API сервера: {e}")


def get_api_server_process():
    """Получить ссылку на процесс API сервера"""
    return api_server_process










