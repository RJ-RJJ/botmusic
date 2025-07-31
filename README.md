# 🎵 Discord Music Bot

A powerful Discord music bot with playlist support, concurrent loading, and smart auto-continue features.

## 🚀 Features

- **🎵 Music Playback** - Play from YouTube, YouTube Music, and 1000+ sites
- **📀 Smart Playlist Support** - Auto-loads large playlists in batches
- **⚡ Fast Concurrent Loading** - Load multiple songs simultaneously
- **🔄 Auto-Continue** - Background loading for seamless playback
- **🔊 Volume Control** - Adjust volume with visual indicators
- **🔂 Loop Mode** - Loop individual songs
- **🔀 Queue Management** - Shuffle, skip, remove songs
- **🤖 Auto-Disconnect** - Leaves when alone in voice channel
- **☁️ Cloud Ready** - Optimized for Railway, Render, Replit hosting

## 🎮 Commands

### Music Commands
- `?play <song/url/playlist>` - Play music or playlist (⚡ Fast concurrent loading)
- `?pause` / `?resume` - Pause/resume current song
- `?skip` - Skip current song
- `?stop` - Stop music and clear queue
- `?queue` - Show music queue
- `?now` - Show currently playing song
- `?volume [1-100]` - Set/check volume
- `?loop` - Toggle loop mode
- `?shuffle` - Shuffle queue
- `?remove <number>` - Remove song from queue
- `?playlist` - Show playlist status

### Voice Commands
- `?join` - Join your voice channel
- `?leave` - Leave voice channel
- `?summon <channel>` - Join specific channel

## 🛠️ Setup

### Requirements
- Python 3.11+
- FFmpeg (auto-installed on hosting platforms)
- Discord Bot Token

### Local Development
1. Clone this repository
2. Install dependencies: `pip install -r requirements.txt`
3. Create `token.env` file with your Discord bot token:
   ```
   TOKEN=your_bot_token_here
   ```
4. Run: `python bot.py`

### 🚀 Deploy to Cloud (Recommended)
1. Check deployment readiness: `python deploy_check.py`
2. Push to GitHub: `git add . && git commit -m "Deploy" && git push`
3. Deploy to [Railway.app](https://railway.app) or [Render.com](https://render.com)
4. Set `TOKEN` environment variable
5. Bot online 24/7! 🎉

See `DEPLOY.md` for detailed hosting guide.

## 🎵 Examples

```
?play never gonna give you up
?play https://www.youtube.com/watch?v=dQw4w9WgXcQ
?play https://www.youtube.com/playlist?list=PLrAl6rYGsBqGFbvpOklq7_pHVz8Kl7Qwk
?volume 50
?queue
?skip
```

## 📊 Performance

- ⚡ **3-5x faster** playlist loading with concurrent processing
- 🔄 **Background loading** for uninterrupted playback
- 🚀 **Cloud optimized** - faster than local hosting
- 📱 **Responsive** - instant command responses

## 🆘 Support

For hosting issues, check `DEPLOY.md` or the deployment checker:
```bash
python deploy_check.py
```

## 📄 License

MIT License - Feel free to use and modify!
