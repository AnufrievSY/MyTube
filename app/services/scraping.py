import subprocess
import json
import os
import sys
import shutil
from pathlib import Path
from app.utils import log, paths
from app.utils.models import ParsingResult
import uuid
import requests

CUSTOM_FFMPEG_PATH = paths.SERVICE_DATA / 'ffmpeg-7.1.1-essentials_build'/ 'bin' / 'ffmpeg.exe'

def _get_ffmpeg_path() -> str:
    """
    Определяет путь до ffmpeg. Если он не найден — выбрасывает ошибку.
    """
    if CUSTOM_FFMPEG_PATH and Path(CUSTOM_FFMPEG_PATH).exists():
        return str(Path(CUSTOM_FFMPEG_PATH).parent)
    path = shutil.which("ffmpeg")
    if not path:
        raise RuntimeError(
            "❌ ffmpeg не найден.\n"
            "👉 Установи его с https://www.gyan.dev/ffmpeg/builds/\n"
            "или пропиши путь вручную в переменную CUSTOM_FFMPEG_PATH."
        )
    return path


def download_youtube_video(url: str, mode: str = "video") -> ParsingResult:
    """
    Скачивает YouTube-видео или аудио через yt-dlp с использованием локального прокси.

    :param url: Ссылка на видео
    :param mode: 'video' (mp4) или 'audio' (mp3)
    :return: (title, author, абсолютный путь до скачанного файла)
    """
    assert mode in ("video", "audio")
    ext = "mp4" if mode == "video" else "mp3"

    ffmpeg_dir = _get_ffmpeg_path()
    env = os.environ.copy()
    env["PATH"] = ffmpeg_dir + os.pathsep + env["PATH"]

    with open(paths.PROXY, 'r') as f:
        proxy = f.read().strip()
    log.debug(f'get proxy: {proxy}')

    # Получаем метаданные видео (название, автор и т.д.)
    info_proc = subprocess.run(
        [sys.executable, "-m", "yt_dlp", "--proxy", f"http://{proxy}", "-j", url],
        capture_output=True,
        text=True,
        env=env
    )

    if info_proc.returncode != 0:
        log.error(f"[yt-dlp] Не удалось получить метаданные:\n{info_proc.stderr.strip()}")
        raise RuntimeError("Ошибка получения метаинформации.")

    info = json.loads(info_proc.stdout)
    file_name = info.get('id', uuid.uuid4().hex)
    name = info.get("title", "unknown_video")
    author = info.get("uploader") or info.get("channel") or "unknown"
    duration = info.get('duration', 0)

    image_path = paths.SERVICE_DATA / 'default.jpg'
    image_url = info.get('thumbnail')
    if image_url:
        image_response = requests.get(image_url)
        if image_response.status_code == 200:
            image_path = paths.TEMP / f'{file_name}.{ext}'
            with open(image_path, "wb") as f:
                f.write(image_response.content)
        else:
            log.error(f"{image_response.status_code} image download:\n{image_response.content}")

    base_output = paths.TEMP / file_name

    # Формируем команду загрузки
    output_template = f"{base_output}.%(ext)s"
    cmd = [
        sys.executable, "-m", "yt_dlp",
        "--proxy", f"http://{proxy}",
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
    log.debug(f"[yt-dlp] run: {' '.join(cmd)}")
    subprocess.run(cmd, check=True, env=env)


    final_path = base_output.with_suffix(f".{ext}").resolve()

    log.info(f"Saved to: {final_path}")
    return ParsingResult(name=name, author=author, duration=duration, image=image_path, file_path=final_path)


if __name__ == "__main__":
    video_url = 'https://www.youtube.com/watch?v=ZDmUSt4gt-g'
    p = download_youtube_video(video_url, mode="audio")
    print(f"Title: {p.name}\nAuthor: {p.author}\nSaved to: {p.file_path}")

