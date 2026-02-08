#!/usr/bin/env python3
"""Baixa músicas de uma playlist pública do Spotify sem API oficial."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from html import unescape
from pathlib import Path
from typing import Any, Iterable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import yt_dlp

INVALID_FILENAME_CHARS = re.compile(r"[\\/:*?\"<>|]")
NEXT_DATA_PATTERN = re.compile(
    r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', re.DOTALL
)


@dataclass
class Track:
    title: str
    artists: list[str]

    @property
    def query(self) -> str:
        return f"{' '.join(self.artists)} - {self.title}" if self.artists else self.title

    @property
    def filename(self) -> str:
        artists = ", ".join(self.artists) if self.artists else "Artista Desconhecido"
        raw = f"{artists} - {self.title}"
        cleaned = INVALID_FILENAME_CHARS.sub("_", raw)
        return cleaned.strip()[:180]


def extract_playlist_id(playlist_ref: str) -> str:
    if "spotify.com/playlist/" in playlist_ref:
        match = re.search(r"playlist/([a-zA-Z0-9]+)", playlist_ref)
        if not match:
            raise ValueError("Não foi possível extrair o ID da playlist da URL fornecida.")
        return match.group(1)
    return playlist_ref


def normalize_playlist_url(playlist_ref: str) -> str:
    if playlist_ref.startswith("http://") or playlist_ref.startswith("https://"):
        return playlist_ref
    return f"https://open.spotify.com/playlist/{extract_playlist_id(playlist_ref)}"


def _walk(obj: Any) -> Iterable[Any]:
    if isinstance(obj, dict):
        yield obj
        for value in obj.values():
            yield from _walk(value)
    elif isinstance(obj, list):
        for item in obj:
            yield from _walk(item)


def _extract_tracks_from_next_data(next_data: dict) -> list[Track]:
    found: dict[tuple[str, tuple[str, ...]], Track] = {}

    for node in _walk(next_data):
        if not isinstance(node, dict):
            continue

        # Estruturas comuns com metadados de faixa na página pública do Spotify
        name = node.get("name") or node.get("title")
        artists_data = node.get("artists")

        if not isinstance(name, str):
            continue

        artists: list[str] = []
        if isinstance(artists_data, dict):
            items = artists_data.get("items", [])
            for artist in items:
                if isinstance(artist, dict) and isinstance(artist.get("profile"), dict):
                    artist_name = artist["profile"].get("name")
                    if isinstance(artist_name, str) and artist_name.strip():
                        artists.append(artist_name.strip())
        elif isinstance(artists_data, list):
            for artist in artists_data:
                if isinstance(artist, dict):
                    artist_name = artist.get("name")
                    if isinstance(artist_name, str) and artist_name.strip():
                        artists.append(artist_name.strip())
                elif isinstance(artist, str) and artist.strip():
                    artists.append(artist.strip())

        uri = node.get("uri")
        if isinstance(uri, str) and not uri.startswith("spotify:track:"):
            continue

        if not artists:
            continue

        title = name.strip()
        if not title:
            continue

        key = (title.lower(), tuple(a.lower() for a in artists))
        found[key] = Track(title=title, artists=artists)

    return list(found.values())


def fetch_playlist_tracks_without_spotify_api(playlist_ref: str) -> tuple[str, list[Track]]:
    playlist_url = normalize_playlist_url(playlist_ref)
    request = Request(
        playlist_url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
        },
    )

    try:
        with urlopen(request, timeout=30) as response:
            html = response.read().decode("utf-8", errors="ignore")
    except HTTPError as exc:
        raise RuntimeError(f"Falha HTTP ao abrir playlist ({exc.code}).") from exc
    except URLError as exc:
        raise RuntimeError(f"Falha de rede ao abrir playlist: {exc.reason}") from exc

    match = NEXT_DATA_PATTERN.search(html)
    if not match:
        raise RuntimeError(
            "Não foi possível extrair metadados da playlist da página pública do Spotify."
        )

    try:
        next_data = json.loads(unescape(match.group(1)))
    except json.JSONDecodeError as exc:
        raise RuntimeError("Falha ao decodificar os metadados da playlist.") from exc

    tracks = _extract_tracks_from_next_data(next_data)
    playlist_name = extract_playlist_id(playlist_ref)

    # tenta pegar nome da playlist no JSON
    for node in _walk(next_data):
        if isinstance(node, dict):
            node_type = node.get("__typename")
            if node_type == "Playlist" and isinstance(node.get("name"), str):
                playlist_name = node["name"].strip() or playlist_name
                break

    return playlist_name, tracks


def download_tracks(tracks: Iterable[Track], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    ydl_options = {
        "format": "bestaudio/best",
        "noplaylist": True,
        "quiet": False,
        "no_warnings": True,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ],
    }

    with yt_dlp.YoutubeDL(ydl_options) as ydl:
        for index, track in enumerate(tracks, start=1):
            target_file = output_dir / f"{track.filename}.mp3"
            if target_file.exists():
                print(f"[{index}] Já existe, pulando: {target_file.name}")
                continue

            search_query = f"ytsearch1:{track.query} audio"
            print(f"[{index}] Baixando: {track.query}")
            ydl.params.update({"outtmpl": str(output_dir / f"{track.filename}.%(ext)s")})

            try:
                ydl.download([search_query])
            except yt_dlp.utils.DownloadError as exc:
                print(f"[{index}] Falha ao baixar '{track.query}': {exc}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Recebe URL/ID de playlist pública do Spotify e baixa músicas localmente "
            "sem credenciais da API oficial."
        )
    )
    parser.add_argument("playlist", help="URL ou ID da playlist do Spotify")
    parser.add_argument(
        "--output",
        "-o",
        default="downloads",
        help="Diretório de saída para as músicas (padrão: downloads)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        playlist_name, tracks = fetch_playlist_tracks_without_spotify_api(args.playlist)
    except Exception as exc:
        print(f"Erro ao obter playlist do Spotify sem API oficial: {exc}")
        return 1

    if not tracks:
        print(
            "Nenhuma faixa encontrada. A playlist pode ser privada ou o formato da página mudou."
        )
        return 0

    print(f"Playlist: {playlist_name}")
    print(f"Total de músicas: {len(tracks)}")

    download_tracks(tracks, Path(args.output) / extract_playlist_id(args.playlist))
    print("Download concluído.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
