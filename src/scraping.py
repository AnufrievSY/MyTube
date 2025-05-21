import subprocess
import json
import os
import sys
import shutil
from pathlib import Path

from common import ROOT, log

# Путь до файла, где хранится порт прокси-сервера
PROXY_FILE = ROOT / "common" / "proxy_port.txt"

# Папка, в которую сохраняются все медиафайлы
OUTPUT_DIR = ROOT / "temp"
OUTPUT_DIR.mkdir(exist_ok=True)

# Если не хочешь прописывать ffmpeg в PATH — можно указать путь напрямую
CUSTOM_FFMPEG_PATH = ROOT / r'common\ffmpeg-7.1.1-essentials_build\bin\ffmpeg.exe'


def sanitize_filename(name: str) -> str:
    """
    Преобразует название в безопасный для файловой системы формат.
    """
    return "".join(c if c.isalnum() or c in " ._-()" else "_" for c in name)


def get_ffmpeg_path() -> str:
    """
    Определяет путь до ffmpeg. Если он не найден — выбрасывает ошибку.
    """
    if CUSTOM_FFMPEG_PATH and Path(CUSTOM_FFMPEG_PATH).exists():
        return str(Path(CUSTOM_FFMPEG_PATH))
    path = shutil.which("ffmpeg")
    if not path:
        raise RuntimeError(
            "❌ ffmpeg не найден.\n"
            "👉 Установи его с https://www.gyan.dev/ffmpeg/builds/\n"
            "или пропиши путь вручную в переменную CUSTOM_FFMPEG_PATH."
        )
    return path


def download_youtube_video(url: str, mode: str = "video", verbose: bool = False) -> tuple[str, str, str]:
    """
    Скачивает YouTube-видео или аудио через yt-dlp с использованием локального прокси.

    :param url: Ссылка на видео
    :param mode: 'video' (mp4) или 'audio' (mp3)
    :param verbose: Выводить команды и логи yt-dlp
    :return: (title, author, абсолютный путь до скачанного файла)
    """
    assert mode in ("video", "audio")

    ffmpeg_path = get_ffmpeg_path()
    env = os.environ.copy()
    if CUSTOM_FFMPEG_PATH:
        ffmpeg_dir = str(Path(CUSTOM_FFMPEG_PATH).parent)
        env["PATH"] = ffmpeg_dir + os.pathsep + env["PATH"]

    with open(PROXY_FILE, 'r') as f:
        proxy = f"http://{f.read().strip()}"
    log.debug(f'get proxy: {proxy}')
    # Получаем метаданные видео (название, автор и т.д.)
    info_proc = subprocess.run(
        [sys.executable, "-m", "yt_dlp", "--proxy", proxy, "-j", url],
        capture_output=True,
        text=True,
        env=env
    )
    if info_proc.returncode != 0:
        log.error(f"[yt-dlp] Не удалось получить метаданные:\n{info_proc.stderr.strip()}")
        raise RuntimeError("Ошибка получения метаинформации.")

    info = json.loads(info_proc.stdout)
    title = sanitize_filename(info.get("title", "unknown_video"))
    author = info.get("uploader") or info.get("channel") or "unknown"
    base_output = OUTPUT_DIR / title

    # Формируем команду загрузки
    output_template = f"{base_output}.%(ext)s"
    cmd = [
        sys.executable, "-m", "yt_dlp",
        "--proxy", proxy,
        "--no-playlist",
        "-o", output_template,
        "--quiet",
        "--no-warnings",
        "--progress"
    ]

    if mode == "video":
        cmd += ["-f", "bv[height<=1080]+ba", "--merge-output-format", "mp4"]
    else:
        cmd += ["-f", "bestaudio", "--extract-audio", "--audio-format", "mp3"]

    cmd.append(url)

    # Выполняем загрузку
    if verbose:
        log.debug(f"[yt-dlp] run: {' '.join(cmd)}")
        subprocess.run(cmd, check=True, env=env)
    else:
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True, env=env)

    ext = "mp4" if mode == "video" else "mp3"
    final_path = base_output.with_suffix(f".{ext}").resolve()

    log.info(f"Saved to: {final_path}")
    return title, author, str(final_path)


if __name__ == "__main__":
    video_url = 'https://www.youtube.com/watch?v=ZDmUSt4gt-g'
    title, author, path = download_youtube_video(video_url, mode="audio", verbose=True)
    print(f"Title: {title}\nAuthor: {author}\nSaved to: {path}")
