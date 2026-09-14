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
        
        # Curated airdrops - SIMPLE TASKS ONLY
        self.airdrops = [
            {
                'name': 'BELDEX LOYALTY PROGRAM',
                'hadiah': '50-500 BDX',
                'nilai': 'Rp 60.000 - 600.000',
                'status': 'ACTIVE',
                'website': 'https://quest.beldex.io/loyalty',
                'twitter': 'https://x.com/BeldexOfficial',
                'discord': 'https://discord.gg/beldex',
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
                    'Download MEXC',
                    'Jual BDX ke Rupiah',
                    'Tarik ke rekening bank',
                ],
                'key': 'beldex_loyalty',
            },
            {
                'name': 'PHAROS NETWORK',
                'hadiah': '$PROS tokens',
                'nilai': 'Bisa dijual',
                'status': 'ACTIVE',
                'website': 'https://pharosnetwork.xyz',
                'twitter': 'https://x.com/PharosNetwork',
                'telegram': 'https://t.me/pharosnetwork',
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
                'key': 'pharos_network',
            },
            {
                'name': 'DEEPBOOK',
                'hadiah': '$DEEP tokens',
                'nilai': 'Bisa dijual',
                'status': 'CLAIM LIVE',
                'website': 'https://deepbook.tech',
                'twitter': 'https://x.com/deepbookv3',
                'steps': [
                    'Buka link Website di Chrome HP',
                    'Connect wallet (Sui)',
                    'Klik Claim Airdrop',
                    'Masukin wallet address',
                    'Done! Token masuk',
                ],
                'cashout': [
                    'Token masuk wallet',
                    'Download MEXC atau Bybit',
                    'Jual token ke Rupiah',
                    'Tarik ke rekening bank',
                ],
                'key': 'deepbook',
            },
            {
                'name': 'CANOPY',
                'hadiah': '$CANOPY tokens',
                'nilai': 'Bisa dijual',
                'status': 'CLAIM LIVE',
                'website': 'https://canopy.finance',
                'twitter': 'https://x.com/CanopyFinance',
                'steps': [
                    'Buka link Website di Chrome HP',
                    'Connect wallet',
                    'Klik Claim',
                    'Follow Twitter mereka',
                    'Done! Token masuk',
                ],
                'cashout': [
                    'Token masuk wallet',
                    'Jual di exchange',
                    'Tarik ke rekening bank',
                ],
                'key': 'canopy',
            },
            {
                'name': 'YAKKAMON',
                'hadiah': 'NFT mint',
                'nilai': 'Bisa dijual',
                'status': 'MINT LIVE',
                'website': 'https://yakkamon.xyz',
                'twitter': 'https://x.com/YakkamonNFT',
                'steps': [
                    'Buka link Website di Chrome HP',
                    'Connect wallet',
                    'Klik Mint',
                    'Mint NFT gratis',
                    'Done! NFT masuk wallet',
                ],
                'cashout': [
                    'NFT masuk wallet',
                    'Jual di marketplace',
                    'Tarik ke rekening bank',
                ],
                'key': 'yakkamon',
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
        cutoff = (datetime.now() - timedelta(days=14)).isoformat()
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
        if airdrop.get('telegram'):
            msg += f"Telegram: {airdrop['telegram']}\n"
        if airdrop.get('discord'):
            msg += f"Discord: {airdrop['discord']}\n"
        
        msg += "\n--- CARA IKUTAN ---\n\n"
        for i, step in enumerate(airdrop['steps'], 1):
            msg += f"Step {i}: {step}\n"
        
        msg += "\n--- CARA AMBIL UANGNYA ---\n\n"
        for i, step in enumerate(airdrop['cashout'], 1):
            msg += f"{i}. {step}\n"
        
        msg += "\n==============================\n"
        msg += "Task simple: Follow + Join + Submit\n"
        msg += "100% GRATIS!\n"
        msg += "Jangan kasih seed phrase = SCAM!\n"
        
        return msg
    
    def format_no_new(self):
        msg = "BELUM ADA AIRDROP BARU\n"
        msg += "==============================\n\n"
        msg += f"Update: {datetime.now().strftime('%d %b %Y %H:%M')}\n\n"
        msg += "Semua airdrop udah dikirim.\n"
        msg += "Tunggu 6 jam lagi!\n\n"
        msg += "==============================\n"
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
            msg = self.format_no_new()
            success = self._send_telegram(msg)
            self._log(f"No new airdrops - sent: {success}")
        
        return True

if __name__ == "__main__":
    hunter = AirdropHunterV4()
    hunter.run()
