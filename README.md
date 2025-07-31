# Discord Music Bot OLd

A simple Discord music bot with slash commands for playing music in your Discord server.

## Features

- `/play` - Play a song from YouTube or other supported platforms
- `/queue` - Display the current music queue
- `/skip` - Skip the current song
- `/stop` - Stop the music and clear the queue

## Requirements

- Node.js 16.9.0 or newer
- Discord.js v14
- FFmpeg

## Setup

1. Clone this repository
2. Install dependencies with `npm install`
3. Create a Discord bot on the [Discord Developer Portal](https://discord.com/developers/applications)
4. Enable the following Privileged Gateway Intents for your bot:
   - Server Members Intent
   - Message Content Intent
5. Copy your bot token and client ID
6. Edit the `.env` file and add your bot token and client ID:
   ```
   TOKEN=your_bot_token_here
   CLIENT_ID=your_client_id_here
   ```
7. Deploy the slash commands with `npm run deploy`
8. Start the bot with `npm start`

## Invite the Bot

To invite the bot to your server, use the following URL, replacing `YOUR_CLIENT_ID` with your bot's client ID:

```
https://discord.com/api/oauth2/authorize?client_id=YOUR_CLIENT_ID&permissions=277083450688&scope=bot%20applications.commands
```

The bot needs the following permissions:
- Send Messages
- Embed Links
- Attach Files
- Read Message History
- Add Reactions
- Connect to Voice Channels
- Speak in Voice Channels
- Use Voice Activity
- Use Application Commands

## Usage

Once the bot is in your server and running, you can use the following slash commands:

- `/play [song]` - Play a song or add it to the queue
- `/queue` - Display the current music queue
- `/skip` - Skip the current song
- `/stop` - Stop the music and clear the queue

## License

This project is licensed under the MIT License - see the LICENSE file for details.