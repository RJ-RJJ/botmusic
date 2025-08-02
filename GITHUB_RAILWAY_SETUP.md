# 🚀 GitHub + Railway Deployment Guide

## Setup GitHub Repository dengan Struktur Baru

### 1. **Persiapan Repository**

```bash
# Initialize git (jika belum)
git init

# Add semua file baru
git add .

# Commit perubahan
git commit -m "🔧 Refactor: Modular structure + Memory Management

✨ Features:
- Pecah bot.py (1856 → 97 lines) menjadi modular structure
- Implementasi memory management dengan psutil
- Tambah memory monitoring commands (?memory, ?cleanup)
- Auto memory cleanup setiap 5 menit

📁 Structure:
- config/ - Configuration & settings
- utils/ - Utility classes & helpers  
- cogs/ - Discord command groups
- bot.py - Main entry point (97 lines only!)"

# Push ke GitHub
git branch -M main
git remote add origin https://github.com/[USERNAME]/[REPO-NAME].git
git push -u origin main
```

### 2. **File Penting untuk GitHub**

#### ✅ **Pastikan file ini ada di repo:**
- `bot.py` (main entry point)
- `requirements.txt` (dengan psutil)
- `Dockerfile` (untuk Railway)
- `render.yaml` (backup hosting)
- `.gitignore` (exclude token.env)

#### ❌ **Jangan push file ini:**
- `token.env` (sudah di .gitignore)
- `__pycache__/` folders
- `.venv/` folder
- `bot_old.py` (backup lokal aja)

---

## 🚂 Railway Deployment Setup

### 1. **Connect Repository ke Railway**

1. Login ke [Railway.app](https://railway.app)
2. Click **"New Project"**
3. Select **"Deploy from GitHub repo"**
4. Pilih repository bot Discord Anda
5. Railway akan auto-detect sebagai Python project

### 2. **Environment Variables Setup**

Di Railway Dashboard → Variables, tambahkan:

```env
TOKEN=your_discord_bot_token_here
PYTHONUNBUFFERED=1
PYTHONDONTWRITEBYTECODE=1
```

### 3. **Deploy Configuration**

Railway akan otomatis menggunakan:
- `requirements.txt` → Install dependencies
- `Dockerfile` → Build container  
- `bot.py` → Run aplikasi

### 4. **Verifikasi Deployment**

Check di Railway Logs:
```
✅ Bot ready! Logged in as YourBot#1234
🎵 Connected to X servers
🎵 Using Python with yt-dlp
🎵 FFmpeg: System FFmpeg (/usr/bin/ffmpeg)
🎧 Status: Simple 3-status rotation system started
🧠 Memory manager started with 5-minute cleanup cycle
```

---

## 🔄 Auto-Sync GitHub ↔ Railway

### **Railway akan otomatis deploy ketika:**
- Push ke branch `main`
- Merge pull request
- Any commit ke repository

### **Monitoring Deployment:**
1. **Railway Dashboard** → Your Project → Deployments
2. **Real-time logs** → Monitor startup & errors
3. **Metrics** → CPU, RAM, Network usage

---

## 🆕 Fitur Baru Setelah Deployment

### **Commands Baru:**

#### **Memory Management:**
```
?memory    # Lihat memory usage & statistics
?cleanup   # Force memory cleanup
```

#### **Enhanced Commands:**
```
?debug     # Lebih detail dengan memory info
?stats     # Termasuk memory statistics
```

### **Auto Features:**
- ✅ **Auto memory cleanup** setiap 5 menit
- ✅ **Memory leak prevention**
- ✅ **Resource tracking**
- ✅ **FFmpeg process cleanup**

---

## 🔧 Troubleshooting

### **Jika Deploy Gagal:**

#### **1. Dependencies Error:**
```bash
# Update requirements.txt
echo "psutil>=5.9.0" >> requirements.txt
git add requirements.txt
git commit -m "Add psutil dependency"
git push
```

#### **2. Import Error:**
```bash
# Test locally dulu
python -c "import config; import utils; import cogs; print('OK')"

# Jika error, fix dulu baru push
```

#### **3. FFmpeg Missing:**
Railway sudah include FFmpeg, tapi jika error:
```dockerfile
# Update Dockerfile line 8-11
RUN apt-get update && apt-get install -y \
    ffmpeg \
    git \
    && rm -rf /var/lib/apt/lists/*
```

### **Monitoring Health:**

#### **Memory Usage:**
```
?memory     # Check current memory
?cleanup    # Force cleanup jika tinggi
```

#### **Bot Status:**
```
?debug      # Full system diagnostics
?stats      # Performance statistics
```

---

## 📊 Keuntungan Setup Ini

### **Development:**
- ✅ **Modular code** → Easier debugging
- ✅ **Memory management** → Stable hosting
- ✅ **Auto cleanup** → No memory leaks
- ✅ **Real-time monitoring** → Performance tracking

### **Deployment:**  
- ✅ **Auto-sync** → Push to deploy
- ✅ **Resource efficiency** → Lower hosting costs
- ✅ **Stability** → Fewer crashes
- ✅ **Monitoring** → Easy troubleshooting

### **Maintenance:**
- ✅ **Easy updates** → Modular structure
- ✅ **Team development** → Multiple devs
- ✅ **Testing** → Individual components
- ✅ **Scaling** → Add features easily

---

## 🎯 Next Steps Rekomendasi

1. **Deploy & Test** → Pastikan semua bekerja
2. **Monitor Memory** → Check `?memory` berkala  
3. **Add Features** → Lanjut optimizations lain
4. **Database Integration** → SQLite untuk persistensi
5. **Error Handling** → Centralized error management
6. **Caching System** → Metadata & URL caching

---

**🚀 Ready to deploy! Push ke GitHub dan Railway akan handle the rest!**