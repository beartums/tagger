# Self-hosting guide

tagger is a single container that serves the API and the built UI on port 8000.
It needs two mounts: your music library (read/write, since it edits tags and can
rename/move files) and a config directory that holds `library.db` and
`settings.json`.

## docker-compose

```yaml
services:
  tagger:
    image: ghcr.io/beartums/tagger:latest   # or `build: .` to build locally
    container_name: tagger
    restart: unless-stopped
    ports:
      - "8000:8000"
    volumes:
      - /srv/music:/music                    # your library (read/write)
      - tagger-config:/config                # library.db + settings.json
    environment:
      - TAGGER_PASSWORD=change-me            # omit to run without a login
      - TAGGER_SECURE_COOKIE=1               # set when served over HTTPS
      # - TAGGER_SECRET_KEY=...              # encrypts API keys in settings.json
      # - TAGGER_LIBRARY_ROOTS=/music/Shared:/music/Libraries/*   # see Library roots
      # - ACOUSTID_API_KEY=...               # optional fingerprint lookup

volumes:
  tagger-config:
```

`docker compose up -d`, then open http://localhost:8000.

## Authentication & HTTPS

- Set `TAGGER_PASSWORD` to require a login. The session is an HttpOnly cookie;
  failed logins are rate-limited per IP.
- When you serve tagger over HTTPS (recommended for anything beyond a trusted
  LAN), also set `TAGGER_SECURE_COOKIE=1` so the session cookie is marked
  `Secure` and never sent over plain HTTP.

### Reverse proxy (Caddy)

Caddy gives you automatic HTTPS with a one-line config:

```
tagger.example.com {
    reverse_proxy localhost:8000
}
```

### Reverse proxy (nginx)

```nginx
server {
    listen 443 ssl;
    server_name tagger.example.com;
    # ssl_certificate / ssl_certificate_key ...

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_http_version 1.1;                 # audio streaming + range
    }
}
```

## Library roots

Layouts (the file-structure templates) are relative to a *library root*, and
Tagger never moves a file out of the deepest root that contains it. By default
the root is the music mount; set `TAGGER_LIBRARY_ROOTS` (colon-separated,
globs allowed) or Settings → Libraries when the mount holds several
libraries, e.g. `/music/Shared:/music/Libraries/*`.

## API keys

The AcoustID key, Discogs token and LRCLIB key entered in Settings are saved
in `settings.json`. Set `TAGGER_SECRET_KEY` to a Fernet key (see the README)
and they're stored encrypted; keys already saved in plain text are encrypted
at the next start. Keep the secret key out of the config volume (an env file,
Docker secret or Kubernetes Secret). If it's lost, enter the keys again.

## Health check

`GET /api/health` returns `{"status":"ok","version":"…"}` without auth — use it
for a container `HEALTHCHECK` or an uptime monitor:

```yaml
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')"]
      interval: 30s
      timeout: 5s
      retries: 3
```

## Backups

Everything worth keeping lives in the config volume: `library.db` (the index,
staged changes, groups and undo history) and `settings.json`. Back that volume
up. The index can always be rebuilt with a rescan, but settings, staged
changes and undo history can't. Without `TAGGER_SECRET_KEY`, the backup holds
your API keys in plain text.

Deleted files are moved to `/config/trash` (recoverable via Undo) until you
empty the trash from Settings.

## Optional external tools

Three features shell out to a binary and hide themselves when it isn't there,
so a missing tool is never fatal — it just removes that feature:

| Feature | Needs | In the image? |
|---|---|---|
| ReplayGain scanning | `rsgain` or `loudgain` | `rsgain`, yes |
| Spectrograms | `ffmpeg` | yes |
| AcoustID fingerprinting | `fpcalc` (chromaprint) + an API key | `fpcalc`, yes |

Rendered spectrograms are cached under `/config/spectrograms`, keyed by track
and file mtime, so a file is only rendered once until it changes. The cache is
disposable — delete it any time to reclaim the space.

## Updating

```bash
docker compose pull && docker compose up -d
```

Schema changes migrate automatically on start; your library and settings are
preserved.
