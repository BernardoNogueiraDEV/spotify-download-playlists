# Spotify Playlist Downloader (sem API oficial)

Sistema em Python que recebe a URL de uma playlist do Spotify e baixa as músicas localmente em MP3 **sem exigir credenciais da API do Spotify**.

## Correção do erro de DRM
Se você recebeu o erro:

```text
ERROR: [DRM] The requested site is known to use DRM protection
```

isso acontecia porque o `yt-dlp` estava tentando extrair diretamente do Spotify.
Agora o script:
1. Lê os metadados da playlist pública pelo HTML/JSON da página do Spotify.
2. Usa `yt-dlp` apenas para buscar e baixar o áudio no YouTube.

## Pré-requisitos
- Python 3.10+
- `ffmpeg` instalado no sistema
- `yt-dlp` instalado (via `requirements.txt`)

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
- Funciona para playlists públicas.
- Downloads dependem da disponibilidade dos vídeos no YouTube.
- O script pula músicas já baixadas (mesmo nome de arquivo).
