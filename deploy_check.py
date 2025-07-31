#!/usr/bin/env python3
"""
🚀 Discord Music Bot - Deployment Readiness Checker
Run this before deploying to check if everything is ready!
"""

import os
import sys
from pathlib import Path

def check_file_exists(filename, required=True):
    """Check if a file exists"""
    exists = Path(filename).exists()
    status = "✅" if exists else ("❌" if required else "⚠️")
    print(f"{status} {filename}: {'Found' if exists else 'Missing'}")
    return exists

def check_gitignore():
    """Check if .gitignore excludes FFmpeg"""
    if not Path('.gitignore').exists():
        print("❌ .gitignore: Missing")
        return False
    
    with open('.gitignore', 'r') as f:
        content = f.read()
    
    has_ffmpeg = 'ffmpeg/' in content
    has_token = 'token.env' in content
    
    status = "✅" if (has_ffmpeg and has_token) else "❌"
    print(f"{status} .gitignore: {'Properly configured' if (has_ffmpeg and has_token) else 'Missing FFmpeg/token exclusions'}")
    return has_ffmpeg and has_token

def check_requirements():
    """Check requirements.txt content"""
    if not Path('requirements.txt').exists():
        print("❌ requirements.txt: Missing")
        return False
    
    with open('requirements.txt', 'r') as f:
        requirements = f.read().lower()
    
    needed = ['discord.py', 'yt-dlp', 'python-dotenv']
    missing = [req for req in needed if req not in requirements]
    
    if not missing:
        print("✅ requirements.txt: All dependencies found")
        return True
    else:
        print(f"❌ requirements.txt: Missing {', '.join(missing)}")
        return False

def check_token():
    """Check if token is available"""
    from dotenv import load_dotenv
    load_dotenv('token.env')
    
    token = os.getenv('TOKEN')
    if token:
        print("✅ Discord Token: Found in environment")
        return True
    else:
        print("⚠️ Discord Token: Not found (normal for hosting)")
        print("   Make sure to set TOKEN environment variable in your hosting platform!")
        return True  # Not a blocker for deployment

def main():
    print("🚀 Discord Music Bot - Deployment Readiness Check\n")
    
    checks = []
    
    print("📁 Required Files:")
    checks.append(check_file_exists('bot.py'))
    checks.append(check_file_exists('requirements.txt'))
    checks.append(check_requirements())
    
    print("\n🐳 Deployment Files:")
    checks.append(check_file_exists('Dockerfile'))
    checks.append(check_file_exists('railway.json', required=False))
    checks.append(check_file_exists('render.yaml', required=False))
    
    print("\n🔧 Configuration:")
    checks.append(check_gitignore())
    checks.append(check_token())
    
    print(f"\n📊 Results:")
    passed = sum(checks)
    total = len(checks)
    
    if passed >= total - 1:  # Allow one warning (token)
        print("🎉 READY FOR DEPLOYMENT!")
        print("\n🚀 Next Steps:")
        print("1. Push to GitHub: git add . && git commit -m 'Ready for hosting' && git push")
        print("2. Go to Railway.app or Render.com")
        print("3. Deploy from GitHub repository")
        print("4. Set TOKEN environment variable")
        print("5. Your bot will be online 24/7! 🎵")
    else:
        print(f"❌ NOT READY - Fix {total - passed} issues above")
        sys.exit(1)

if __name__ == "__main__":
    main()