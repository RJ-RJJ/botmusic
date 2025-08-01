# 🚄 Railway Trial Status System

Bot sekarang menampilkan status Railway trial secara otomatis di bot status dan menyediakan command untuk monitoring!

## ✨ Features Baru

### 🔄 **Dynamic Bot Status (Auto-Rotating)**
Bot status berubah setiap 15 detik:
- `🎵 [Song Name]` - Saat memutar musik
- `Listening to ?help` - Command help
- `Watching Trial: 29d left` - Sisa hari trial
- `Watching Credit: $4.81` - Sisa credit
- `Listening to 🎵 Music Bot Ready` - Default

### 📊 **Command Baru**

#### `?railway` (aliases: `?trial`, `?status`)
Menampilkan detail status trial Railway:
- ✅ Days remaining (dengan color coding)
- 💰 Credit remaining (dengan warning)
- 🚨 Action required jika trial hampir habis
- 📊 Usage info dan estimasi biaya

#### `?update_trial [date]` (aliases: `?set_trial`)
Update tanggal mulai trial:
```bash
?update_trial 2025-01-31    # Set tanggal trial start
?update_trial               # Show current config
```

---

## 🔧 Setup Instructions

### **1. Update Trial Start Date**
Edit di `bot.py` line 31-36:
```python
RAILWAY_CONFIG = {
    'trial_start_date': '2025-01-31',   # 📅 UBAH KE TANGGAL MULAI TRIAL
    'initial_credit': 5.00,            # 💰 $5 initial credit
    'trial_duration_days': 30,         # ⏰ 30 hari trial
    'estimated_monthly_cost': 3.00     # 📊 Estimasi biaya per bulan
}
```

### **2. Alternative: Use Command**
```bash
?update_trial 2025-01-31
```

---

## 🎯 How It Works

### **Status Calculation:**
```
Days Remaining = 30 - (Today - Trial Start Date)
Credit Used = Days Elapsed × ($3.00 ÷ 30)
Credit Remaining = $5.00 - Credit Used
```

### **Status Display Logic:**
- **Good (✅):** >7 days left
- **Warning (⚠️):** 3-7 days left  
- **Critical (🔴):** 1-3 days left
- **Expired (❌):** 0 days left

### **Credit Status:**
- **Healthy (💰):** >$3.00
- **Low (⚠️):** $1.00-$3.00
- **Critical (🔴):** $0.01-$1.00
- **Depleted (❌):** $0.00

---

## 📱 User Experience

### **Bot Status Examples:**
```
Listening to ?help
Watching Trial: 25d left
Watching Credit: $4.20
🎵 Bad Habits - Ed Sheeran
```

### **Command Examples:**
```bash
?railway
# Shows detailed trial status with colorful embed

?update_trial 2025-02-01
# ✅ Railway Configuration Updated
# 📅 New Trial Start Date: 2025-02-01
# 📊 Updated Status: Days remaining: 29, Credit remaining: $5.00
```

---

## 🚨 Important Notes

### **⚠️ Limitations:**
- **Estimation only** - not connected to Railway API
- **Manual tracking** - update tanggal trial sendiri
- **Linear calculation** - actual usage bisa beda

### **🔧 Maintenance:**
1. **Set tanggal trial start** yang akurat
2. **Monitor di Railway dashboard** untuk usage real
3. **Update estimasi** jika bot usage berubah
4. **Add payment method** sebelum trial habis

### **💡 Tips:**
- Status bot berubah setiap 15 detik
- Command `?railway` untuk detail lengkap
- Warning muncul 3 hari sebelum expired
- Bot tetap jalan setelah trial (dengan payment method)

---

## 🆕 Updated Help Commands

### **New in `?help`:**
```
🔧 Troubleshooting
?railway - Check hosting trial status & credits
```

### **All Railway Commands:**
```bash
?railway        # Detailed trial status
?trial          # Alias for ?railway  
?status         # Alias for ?railway
?update_trial   # Update trial config
?set_trial      # Alias for ?update_trial
```

---

**🎉 Sekarang bot otomatis nunjukin sisa trial Railway di status dan ada command lengkap buat monitoring!** 🚄✨