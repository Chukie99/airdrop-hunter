import requests
import json
import os
import re
import subprocess
from datetime import datetime, timedelta

class AirdropHunterV4:
    def __init__(self):
        self.telegram_bot_token = os.environ.get('TELEGRAM_BOT_TOKEN', '')
        self.telegram_chat_id = os.environ.get('TELEGRAM_CHAT_ID', '')
        self.seen_file = "config/seen_airdrops.json"
        self.seen = self._load_seen()
        
        # Curated verified airdrops - updated manually
        self.airdrops = [
            {
                'name': 'BELDEX LOYALTY PROGRAM',
                'hadiah': '50-500 BDX',
                'nilai': 'Rp 60.000 - 600.000',
                'status': 'ACTIVE',
                'website': 'https://quest.beldex.io/loyalty',
                'twitter': 'https://x.com/BeldexOfficial',
                'discord': 'https://discord.gg/beldex',
                'wallet': 'Trust Wallet',
                'wallet_download': 'https://play.google.com/store/apps/details?id=com.trustwallet.dropdown',
                'steps': [
                    'Buka link Website di Chrome HP',
                    'Klik Connect Wallet',
                    'Pilih Trust Wallet',
                    'Klik Allow',
                    'Klik link Twitter, Follow',
                    'Klik link Discord, Join server',
                    'Retweet postingan terbaru',
                    'Klik Submit di website',
                    'Done! Points masuk',
                ],
                'cashout': [
                    'Points dikonversi ke token BDX',
                    'Download MEXC: https://play.google.com/store/apps/details?id=app.mexc',
                    'Daftar + verifikasi KYC (foto KTP)',
                    'Kirim BDX dari Trust Wallet ke MEXC',
                    'Jual BDX ke Rupiah',
                    'Tarik ke rekening bank',
                ],
                'info': 'CoinGecko listed, Team terverifikasi, 100% GRATIS',
                'key': 'beldex_loyalty',
            },
            {
                'name': 'GRASS PROTOCOL',
                'hadiah': '$GRASS tokens',
                'nilai': 'Bisa dijual langsung',
                'status': 'SEASON 3',
                'website': 'https://www.grass.io/register',
                'twitter': 'https://x.com/getgrass_io',
                'discord': 'https://discord.gg/getgrass',
                'wallet': 'Tidak perlu wallet',
                'wallet_download': '',
                'steps': [
                    'Buka link Website di Chrome HP',
                    'Isi email + password',
                    'Klik Register',
                    'Download Grass extension',
                    'Install di Chrome',
                    'Login pakai email',
                    'Biarkan jalan 24/7',
                    'Points nambah sendiri',
                ],
                'cashout': [
                    'Points ditukar ke $GRASS token',
                    'Download MEXC atau Raydium',
                    'Jual $GRASS ke USDC',
                    'Tarik ke rekening bank',
                ],
                'info': '2M+ users, Backed by top VCs, 100% GRATIS',
                'key': 'grass_protocol',
            },
            {
                'name': 'PHAROS NETWORK',
                'hadiah': '$PROS tokens',
                'nilai': 'Bisa dijual',
                'status': 'ACTIVE',
                'website': 'https://pharosnetwork.xyz',
                'twitter': 'https://x.com/PharosNetwork',
                'discord': 'https://discord.gg/pharosnetwork',
                'wallet': 'Trust Wallet',
                'wallet_download': 'https://play.google.com/store/apps/details?id=com.trustwallet.dropdown',
                'steps': [
                    'Buka link Website di Chrome HP',
                    'Klik Connect Wallet',
                    'Pilih Trust Wallet',
                    'Follow Twitter @PharosNetwork',
                    'Join Telegram group',
                    'Retweet announcement',
                    'Done!',
                ],
                'cashout': [
                    'Token otomatis masuk wallet',
                    'Download MEXC',
                    'Jual token ke Rupiah',
                    'Tarik ke rekening bank',
                ],
                'info': 'Backed by VC, Mainnet launching, 100% GRATIS',
                'key': 'pharos_network',
            },
        ]
    
    def _load_seen(self):
        if os.path.exists(self.seen_file):
            with open(self.seen_file) as f:
                return json.load(f)
        return {}
    
    def _save_seen(self):
        os.makedirs(os.path.dirname(self.seen_file), exist_ok=True)
        with open(self.seen_file, 'w') as f:
            json.dump(self.seen, f, indent=2)
    
    def _log(self, msg):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {msg}")
    
    def _mark_seen(self, key):
        self.seen[key] = datetime.now().isoformat()
        cutoff = (datetime.now() - timedelta(days=7)).isoformat()
        self.seen = {k: v for k, v in self.seen.items() if v > cutoff}
        self._save_seen()
    
    def format_message(self, airdrop):
        msg = "REKOMENDASI HARI INI\n"
        msg += "==============================\n\n"
        msg += f"{airdrop['name']}\n\n"
        msg += f"Hadiah: {airdrop['hadiah']}\n"
        msg += f"Nilai: {airdrop['nilai']}\n"
        msg += f"Status: {airdrop['status']}\n\n"
        
        msg += "--- LINK LANGSUNG ---\n\n"
        msg += f"Website: {airdrop['website']}\n"
        msg += f"Twitter: {airdrop['twitter']}\n"
        msg += f"Discord: {airdrop['discord']}\n\n"
        
        msg += "--- YANG PERLU LO SIAPIN ---\n\n"
        if airdrop['wallet'] != 'Tidak perlu wallet':
            msg += f"1. {airdrop['wallet']}\n"
            if airdrop['wallet_download']:
                msg += f"- Download: {airdrop['wallet_download']}\n"
            msg += "- GRATIS, bikin wallet baru\n"
            msg += "- SIMPAN 12 kata rahasia di kertas!\n\n"
            msg += "2. Akun Twitter\n"
            msg += "3. Akun Discord\n\n"
        else:
            msg += "1. PC/Laptop + Chrome\n"
            msg += "2. Akun email\n"
            msg += "3. Internet stabil\n\n"
        
        msg += "--- CARA IKUTAN ---\n\n"
        for i, step in enumerate(airdrop['steps'], 1):
            msg += f"Step {i}: {step}\n"
        
        msg += "\n--- CARA AMBIL UANGNYA ---\n\n"
        for i, step in enumerate(airdrop['cashout'], 1):
            msg += f"{i}. {step}\n"
        
        msg += "\n--- INFO PROYEK ---\n\n"
        msg += f"{airdrop['info']}\n\n"
        msg += "==============================\n\n"
        msg += "Jangan kasih seed phrase = SCAM!\n"
        
        return msg
    
    def _send_telegram(self, message):
        if not self.telegram_bot_token:
            self._log("Telegram not configured")
            return False
        
        url = f"https://api.telegram.org/bot{self.telegram_bot_token}/sendMessage"
        payload = {
            "chat_id": self.telegram_chat_id,
            "text": message,
            "disable_web_page_preview": True
        }
        
        try:
            response = requests.post(url, json=payload, timeout=10)
            return response.json().get('ok', False)
        except Exception as e:
            self._log(f"Telegram error: {e}")
            return False
    
    def run(self):
        self._log("Airdrop Hunter V4 started!")
        
        # Pick next unseen airdrop
        sent = False
        for airdrop in self.airdrops:
            if airdrop['key'] not in self.seen:
                msg = self.format_message(airdrop)
                success = self._send_telegram(msg)
                self._log(f"Sent: {airdrop['name']} - OK: {success}")
                self._mark_seen(airdrop['key'])
                sent = True
                break
        
        if not sent:
            # All seen, reset and start over
            self._log("All airdrops seen, resetting...")
            self.seen = {}
            self._save_seen()
            self.run()
        
        return True

if __name__ == "__main__":
    hunter = AirdropHunterV4()
    hunter.run()
