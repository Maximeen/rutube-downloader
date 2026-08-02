#!/usr/bin/env python3

"""Download individual videos and playlists from rutube.ru using yt-dlp."""

import argparse
import importlib.util
import re
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse


MIN_YT_DLP_VERSION = (2024, 11, 18)
OUTPUT_TEMPLATE = (
    "%(playlist_title,playlist_id&{}/|)s"
    "%(playlist_index&{} - |)s%(title).180B [%(id)s].%(ext)s"
)


class DownloaderError(RuntimeError):
    """A user-facing downloader error."""


def validate_rutube_url(url):
    parsed = urlparse(url)
    hostname = (parsed.hostname or "").lower()
    if parsed.scheme not in {"http", "https"}:
        raise DownloaderError(f"Ссылка должна начинаться с http:// или https://: {url}")
    if hostname != "rutube.ru" and not hostname.endswith(".rutube.ru"):
        raise DownloaderError(f"Ожидалась ссылка на rutube.ru: {url}")


def find_yt_dlp_command():
    try:
        module_available = importlib.util.find_spec("yt_dlp") is not None
    except (ImportError, ModuleNotFoundError, ValueError):
        module_available = False

    if module_available:
        return [sys.executable, "-m", "yt_dlp"]

    executable = shutil.which("yt-dlp")
    if executable:
        return [executable]

    raise DownloaderError(
        "Не найден yt-dlp. Установите его командой:\n"
        f"  {sys.executable} -m pip install -U \"yt-dlp[default]\""
    )


def get_yt_dlp_version(command):
    try:
        result = subprocess.run(
            [*command, "--version"],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise DownloaderError(f"Не удалось запустить yt-dlp: {exc}") from exc

    version = result.stdout.strip().splitlines()[0] if result.stdout.strip() else ""
    match = re.search(r"(\d{4})\.(\d{1,2})\.(\d{1,2})", version)
    if not match:
        raise DownloaderError(f"Не удалось определить версию yt-dlp: {version or 'пустой ответ'}")

    version_tuple = tuple(int(part) for part in match.groups())
    if version_tuple < MIN_YT_DLP_VERSION:
        minimum = ".".join(str(part) for part in MIN_YT_DLP_VERSION)
        raise DownloaderError(
            f"Версия yt-dlp {version} слишком старая; требуется не ниже {minimum}.\n"
            f"Обновите: {sys.executable} -m pip install -U \"yt-dlp[default]\""
        )
    return version


def quality_format(height):
    if height is None:
        return None
    return f"bv*[height<={height}]+ba/b[height<={height}]"


def build_yt_dlp_args(args, output_dir):
    command_args = [
        "--ignore-config",
        "--yes-playlist" if not args.single else "--no-playlist",
        "--paths",
        str(output_dir),
        "--output",
        OUTPUT_TEMPLATE,
    ]

    format_selector = args.format_selector or quality_format(args.quality)
    if format_selector:
        command_args.extend(["--format", format_selector])

    if not args.no_archive:
        archive = args.archive or output_dir / ".rutube-download-archive.txt"
        command_args.extend(["--download-archive", str(archive)])

    if args.playlist_items:
        command_args.extend(["--playlist-items", args.playlist_items])
    if args.cookies:
        command_args.extend(["--cookies", str(args.cookies)])
    if args.cookies_from_browser:
        command_args.extend(["--cookies-from-browser", args.cookies_from_browser])
    if args.proxy:
        command_args.extend(["--proxy", args.proxy])
    if args.limit_rate:
        command_args.extend(["--limit-rate", args.limit_rate])
    if args.subtitles:
        command_args.extend(["--write-subs", "--sub-langs", "all"])
    if args.thumbnail:
        command_args.append("--write-thumbnail")
    if args.metadata:
        command_args.extend(["--write-info-json", "--write-description"])
    if args.dry_run:
        command_args.extend(
            [
                "--simulate",
                "--flat-playlist",
                "--replace-in-metadata",
                "title",
                r"[\r\n]+",
                " ",
                "--print",
                "%(playlist_index&{} - |)s%(title)s [%(id)s]",
            ]
        )
    if args.verbose:
        command_args.append("--verbose")

    command_args.extend(args.urls)
    return command_args


def build_parser():
    parser = argparse.ArgumentParser(
        description="Скачать видео, плейлист или раздел канала с RuTube через yt-dlp.",
        epilog=(
            "Пример: python rutube_downloader.py "
            "https://rutube.ru/plst/308547/ -o downloads"
        ),
    )
    parser.add_argument("urls", nargs="+", help="Одна или несколько ссылок rutube.ru")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("downloads"),
        help="Каталог для файлов (по умолчанию: downloads)",
    )

    format_group = parser.add_mutually_exclusive_group()
    format_group.add_argument(
        "-q",
        "--quality",
        type=int,
        choices=[360, 480, 720, 1080, 1440, 2160],
        metavar="HEIGHT",
        help="Максимальная высота видео; без параметра скачивается лучшее качество",
    )
    format_group.add_argument(
        "-f",
        "--format",
        dest="format_selector",
        metavar="SELECTOR",
        help="Расширенный селектор формата yt-dlp",
    )

    parser.add_argument(
        "--single",
        action="store_true",
        help="Скачать только видео, даже если ссылка содержит контекст плейлиста",
    )
    parser.add_argument(
        "-I",
        "--playlist-items",
        metavar="ITEMS",
        help="Номера элементов плейлиста, например 1:10,15",
    )
    archive_group = parser.add_mutually_exclusive_group()
    archive_group.add_argument(
        "--archive",
        type=Path,
        help="Свой файл архива уже скачанных видео",
    )
    archive_group.add_argument(
        "--no-archive",
        action="store_true",
        help="Не использовать архив уже скачанных видео",
    )

    cookies_group = parser.add_mutually_exclusive_group()
    cookies_group.add_argument(
        "--cookies",
        type=Path,
        help="Cookies в формате Netscape для закрытых или возрастных видео",
    )
    cookies_group.add_argument(
        "--cookies-from-browser",
        metavar="BROWSER",
        help="Взять cookies из браузера: chrome, edge, firefox и т. п.",
    )
    parser.add_argument("--proxy", help="HTTP/HTTPS/SOCKS-прокси для yt-dlp")
    parser.add_argument(
        "--limit-rate",
        metavar="RATE",
        help="Ограничить скорость, например 5M или 800K",
    )
    parser.add_argument(
        "--subtitles",
        action="store_true",
        help="Сохранить все доступные субтитры рядом с видео",
    )
    parser.add_argument(
        "--thumbnail",
        action="store_true",
        help="Сохранить обложку рядом с видео",
    )
    parser.add_argument(
        "--metadata",
        action="store_true",
        help="Сохранить JSON-метаданные и описание",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Получить список видео, ничего не скачивая",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Подробный лог yt-dlp")
    return parser


def run(args):
    for url in args.urls:
        validate_rutube_url(url)

    if args.cookies and not args.cookies.is_file():
        raise DownloaderError(f"Файл cookies не найден: {args.cookies}")

    command = find_yt_dlp_command()
    version = get_yt_dlp_version(command)
    output_dir = args.output.expanduser()
    if not args.dry_run:
        output_dir.mkdir(parents=True, exist_ok=True)

    if shutil.which("ffmpeg") is None and not args.dry_run:
        print(
            "ПРЕДУПРЕЖДЕНИЕ: ffmpeg не найден. Некоторые форматы не удастся объединить ",
            "в один файл.",
            file=sys.stderr,
        )

    print(f"yt-dlp: {version}", flush=True)
    print(f"Каталог: {output_dir}", flush=True)
    if args.dry_run:
        print("Режим проверки: файлы скачиваться не будут", flush=True)

    result = subprocess.run([*command, *build_yt_dlp_args(args, output_dir)])
    if result.returncode:
        raise DownloaderError(
            f"yt-dlp завершился с кодом {result.returncode}. "
            "Повторите с --verbose; для недоступного в обычном браузере видео "
            "попробуйте --cookies-from-browser."
        )


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        run(args)
    except KeyboardInterrupt:
        print("\nЗагрузка прервана.", file=sys.stderr)
        return 130
    except DownloaderError as exc:
        print(f"ОШИБКА: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
