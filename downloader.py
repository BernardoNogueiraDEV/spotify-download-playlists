#!/usr/bin/env python3
"""Baixa músicas de uma playlist do Spotify sem usar credenciais da API oficial."""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import yt_dlp


INVALID_FILENAME_CHARS = re.compile(r"[\\/:*?\"<>|]")


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


def _extract_track_from_entry(entry: dict) -> Track | None:
    if not entry:
        return None

    # Formato comum no extractor do Spotify do yt-dlp
    artists: list[str] = []
    if isinstance(entry.get("artists"), list):
        for artist in entry["artists"]:
            if isinstance(artist, dict) and artist.get("name"):
                artists.append(artist["name"])
            elif isinstance(artist, str):
                artists.append(artist)

    # Fallbacks para diferentes metadados retornados pelo extractor
    title = entry.get("track") or entry.get("title") or entry.get("alt_title")
    if not artists:
        if entry.get("artist"):
            artists = [entry["artist"]]
        elif entry.get("uploader"):
            artists = [entry["uploader"]]

    if not title:
        return None

    return Track(title=title, artists=artists)


def fetch_playlist_tracks_without_spotify_api(playlist_ref: str) -> tuple[str, list[Track]]:
    playlist_url = normalize_playlist_url(playlist_ref)
    opts = {
        "quiet": True,
        "extract_flat": True,
        "skip_download": True,
        "noplaylist": False,
    }

    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(playlist_url, download=False)

    playlist_name = info.get("title") or extract_playlist_id(playlist_ref)
    entries = info.get("entries") or []

    tracks: list[Track] = []
    for entry in entries:
        track = _extract_track_from_entry(entry)
        if track:
            tracks.append(track)

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
        description="Recebe URL/ID de playlist do Spotify e baixa músicas localmente, sem credenciais da API oficial."
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
        print("Nenhuma faixa encontrada para baixar.")
        return 0

    print(f"Playlist: {playlist_name}")
    print(f"Total de músicas: {len(tracks)}")

    download_tracks(tracks, Path(args.output) / extract_playlist_id(args.playlist))
    print("Download concluído.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
