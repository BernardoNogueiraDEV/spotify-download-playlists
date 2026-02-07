# Spotify Playlist Downloader (sem API oficial)

Sistema em Python que recebe a URL de uma playlist do Spotify e baixa as músicas localmente em MP3 **sem exigir credenciais da API do Spotify**.

## Como funciona
1. Lê as músicas da playlist via extractor do próprio `yt-dlp` (sem `client_id`/`client_secret`).
2. Para cada faixa, realiza busca no YouTube usando título + artista.
3. Baixa o melhor áudio disponível e converte para MP3 (192kbps, via ffmpeg).

## Pré-requisitos
- Python 3.10+
- `ffmpeg` instalado no sistema

## Instalação
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Uso
### Com URL da playlist
```bash
python downloader.py "https://open.spotify.com/playlist/SEU_ID"
```

### Com ID da playlist
```bash
python downloader.py "SEU_ID_DA_PLAYLIST"
```

### Definir diretório de saída
```bash
python downloader.py "https://open.spotify.com/playlist/SEU_ID" -o minhas-musicas
```

Os arquivos são salvos em `<diretorio_saida>/<playlist_id>/`.

## Observações
- Downloads dependem da disponibilidade dos vídeos no YouTube.
- Como não usa API oficial, a extração dos metadados depende do suporte atual do `yt-dlp` ao Spotify.
- O script pula músicas já baixadas (mesmo nome de arquivo).
