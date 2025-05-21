import asyncio
import random
import logging
from common.logger import get_logger

log = get_logger("proxy", lvl=logging.INFO)

BLOCKED = []
TASKS = []

async def main(host: str, port: int):
    """
    Запускает асинхронный сокет-сервер на заданном хосте и порту.
    """
    server = await asyncio.start_server(new_conn, host, port)
    log.info(f"Сервер запущен на {host}:{port}")
    await server.serve_forever()


async def pipe(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    """
    Прокидывает данные от reader к writer, пока соединение активно.
    """
    while not reader.at_eof() and not writer.is_closing():
        try:
            chunk = await reader.read(1500)
            if not chunk:
                break
            writer.write(chunk)
            await writer.drain()
        except Exception as exc:
            log.error("Ошибка в pipe", exc_info=exc)
            break
    writer.close()


async def new_conn(local_reader: asyncio.StreamReader, local_writer: asyncio.StreamWriter):
    """
    Обрабатывает новое подключение клиента. Если это CONNECT-запрос, устанавливает соединение
    с целевым сервером и фрагментирует трафик при необходимости.
    """
    log.debug("Новое подключение")
    http_data = await local_reader.read(1500)
    log.debug(f"Принятые данные от клиента: {http_data[:80]}...")

    try:
        method, target = http_data.split(b"\r\n")[0].split(b" ")[0:2]
        host, port = target.split(b":")
        log.debug(f"Метод: {method}, Хост: {host}, Порт: {port}")
    except Exception as exc:
        log.warning(f"Невозможно распарсить заголовки, соединение закрыто:\n{exc}")
        local_writer.close()
        return

    if method != b"CONNECT":
        log.debug(f"Получен не-CONNECT запрос: {method}")
        local_writer.close()
        return

    local_writer.write(b'HTTP/1.1 200 OK\r\n\r\n')
    await local_writer.drain()
    log.debug("Ответ 200 OK отправлен клиенту")

    try:
        remote_reader, remote_writer = await asyncio.open_connection(host, int(port))
        log.debug(f"Соединение с {host}:{port} установлено")
    except Exception as exc:
        log.error(f"Не удалось подключиться к {host}:{port}", exc_info=exc)
        local_writer.close()
        return

    if port == b'443':
        log.debug("Фрагментация TLS-трафика включена (port 443)")
        await fragment_data(local_reader, remote_writer)

    TASKS.append(asyncio.create_task(pipe(local_reader, remote_writer)))
    TASKS.append(asyncio.create_task(pipe(remote_reader, local_writer)))


async def fragment_data(local_reader: asyncio.StreamReader, remote_writer: asyncio.StreamWriter):
    """
    Фрагментирует данные TLS для обхода DPI. Если домен заблокирован — разбивает
    данные на случайные части, иначе пересылает как есть.
    """
    head = await local_reader.read(5)
    data = await local_reader.read(1500)

    log.debug(f"Начало TLS-потока: head={head}, data_length={len(data)}")

    # Если сайт не из списка блокированных — пересылаем напрямую
    if all(data.find(site) == -1 for site in BLOCKED):
        log.debug("Сайт не заблокирован, отправляем данные напрямую")
        remote_writer.write(head + data)
        await remote_writer.drain()
        return

    log.debug("Обнаружен заблокированный домен — выполняем фрагментацию")
    parts = []
    while data:
        part_len = random.randint(1, len(data))
        part = (
            bytes.fromhex("1603") +
            bytes([random.randint(0, 255)]) +
            int(part_len).to_bytes(2, byteorder='big') +
            data[:part_len]
        )
        parts.append(part)
        data = data[part_len:]

    remote_writer.write(b''.join(parts))
    await remote_writer.drain()
    log.debug(f"Отправлено фрагментов: {len(parts)}")


if __name__ == "__main__":
    try:
        # Читаем список заблокированных доменов
        BLOCKED = [
            line.rstrip().encode()
            for line in open('blacklist.txt', 'r', encoding='utf-8')
            if line.strip()
        ]
        log.debug(f"Загружено доменов в blacklist: {len(BLOCKED)}")

        asyncio.run(main(host='127.0.0.1', port=8881))
    except Exception as e:
        log.critical("Ошибка при запуске прокси-сервера", exc_info=e)
