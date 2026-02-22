# Chord - Discord Music Bot (JioSaavn)

Discord music bot using hybrid commands (`/play` and `;play`) and a cog layout like `cogs/<category>/<cmd>.py`.

## Features

- Hybrid commands (`play`, `skip`, `stop`, `nowplaying`)
- JioSaavn search via `JIOSAAVN_API_BASE_URL` from `.env`
- Voice playback with queue
- `.env` configuration

## Project structure

```text
bot.py
core/
  jiosaavn.py
  music_state.py
cogs/
  music/
    nowplaying.py
    play.py
    skip.py
    stop.py
```

## Setup

1. Install ffmpeg on your machine.
2. Create and activate a virtualenv.
3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Configure env:

```bash
cp .env.example .env
```

Fill `DISCORD_TOKEN` in `.env`.
Optional cleanup settings in `.env`:

- `OWNER_ID` (required for `reload`)
- `JIOSAAVN_API_BASE_URL` (required)
- `AUTO_DELETE_ENABLED=true`
- `AUTO_DELETE_SECONDS=12`

5. Run:

```bash
python bot.py
```

## Commands

- `play <query>`
- `pause`
- `resume`
- `skip`
- `queue`
- `clear`
- `nowplaying`
- `stop`
- `leave`
- `reload` (owner only)
- `ping`

All commands work as both slash and prefix commands.
