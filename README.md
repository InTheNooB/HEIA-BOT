# HEIA-BOT

A Discord bot for HEIA-FR students with automated deadline reminders and old exam search.

## Features

- **Deadline Reminders**: Automatically checks a pinned message daily and sends reminders for upcoming deadlines
- **Old Exam Search**: `/old-exam` command to search and retrieve old exam files

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Create a `.env` file with:
```env
DISCORD_TOKEN=your_token
OPENAI_API_KEY=your_key
RENDU_CHANNEL_ID=channel_id
RENDU_MESSAGE_ID=message_id
GENERAL_CHANNEL_ID=channel_id
```

3. Run the bot:
```bash
python bot.py
```

Or with Docker:
```bash
docker build -t heia-bot .
docker run --env-file .env heia-bot
```

## Usage

Use `/old-exam` in Discord to search for old exams:
```
/old-exam query:"Teleinformatique TE1" year:1ère n:1
```

