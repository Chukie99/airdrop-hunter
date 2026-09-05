import subprocess
import json
import time
import os
import re
from datetime import datetime, timedelta

class AirdropHunter:
    def __init__(self):
        self.config = {
            'telegram_bot_token': os.environ.get('TELEGRAM_BOT_TOKEN', ''),
            'telegram_chat_id': os.environ.get('TELEGRAM_CHAT_ID', ''),
        }
        if not self.config['telegram_bot_token']:
            self._load_config_from_file()
        
        self.seen_file = "config/seen_airdrops.json"
        self.seen = self._load_seen()
        self.log_file = "logs/hunter.log"
        
    def _load_config_from_file(self):
        env_file = "config/.env"
        if os.path.exists(env_file):
            with open(env_file) as f:
                for line in f:
                    if '=' in line and not line.startswith('#'):
                        k, v = line.strip().split('=', 1)
                        self.config[k] = v
    
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
        log_msg = f"[{timestamp}] {msg}"
        print(log_msg)
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)
        with open(self.log_file, 'a') as f:
            f.write(log_msg + "\n")
    
    def _curl_get(self, url, headers=None):
        cmd = ['curl', '-s', '-L', '--max-time', '30']
        if headers:
            for k, v in headers.items():
                cmd.extend(['-H', f'{k}: {v}'])
        cmd.append(url)
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=35)
            return result.stdout
        except Exception as e:
            self._log(f"Curl error: {e}")
            return None
    
    def _send_telegram(self, message):
        token = self.config.get('telegram_bot_token', '')
        chat_id = self.config.get('telegram_chat_id', '')
        
        if not token:
            self._log("Telegram not configured")
            print(f"\n{'='*50}\n{message}\n{'='*50}\n")
            return False
        
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = json.dumps({
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML",
            "disable_web_page_preview": True
        })
        
        cmd = ['curl', '-s', '-X', 'POST', url, 
               '-H', 'Content-Type: application/json',
               '-d', payload]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            resp = json.loads(result.stdout)
            return resp.get('ok', False)
        except Exception as e:
            self._log(f"Telegram error: {e}")
            return False
    
    def _is_new(self, campaign_id):
        return campaign_id not in self.seen
    
    def _mark_seen(self, campaign_id):
        self.seen[campaign_id] = datetime.now().isoformat()
        cutoff = (datetime.now() - timedelta(days=7)).isoformat()
        self.seen = {k: v for k, v in self.seen.items() if v > cutoff}
        self._save_seen()
    
    def _translate_step(self, step):
        """Translate common English terms to Indonesian"""
        translations = [
            ('Visit the', 'Kunjungi'),
            ('Connect Your', 'Hubungkan'),
            ('Solana Wallet', 'Wallet Solana'),
            ('Ethereum Wallet', 'Wallet Ethereum'),
            ('Wallet', 'Wallet'),
            ('Acquire', 'Dapatkan'),
            ('Ensure you have sufficient', 'Pastikan kamu punya cukup'),
            ('in your wallet for', 'di wallet untuk'),
            ('and transaction fees', 'dan biaya transaksi'),
            ('Complete Initial Setup', 'Selesaikan Setup Awal'),
            ('Connect your social media accounts', 'Hubungkan akun media sosial kamu'),
            ('as prompted', 'seperti yang diminta'),
            ('You can purchase', 'Kamu bisa beli'),
            ('directly from', 'langsung dari'),
            ('or use the bridge widget below', 'atau pakai bridge di bawah'),
            ('Bridge funds', 'Bridge dana'),
            ('Follow', 'Follow'),
            ('Join', 'Gabung'),
            ('Telegram Group', 'Grup Telegram'),
            ('Discord Server', 'Server Discord'),
            ('Twitter', 'Twitter/X'),
            ('Like', 'Like'),
            ('Retweet', 'Retweet'),
            ('Submit', 'Kirim'),
            ('Enter', 'Masukkan'),
            ('Your', 'Kamu'),
            ('Address', 'Alamat'),
            ('Claim', 'Klaim'),
            ('Stake', 'Stake'),
            ('Deposit', 'Deposit'),
            ('Trade', 'Trade'),
            ('Swap', 'Swap'),
            ('Mint', 'Mint'),
            ('Platform', 'Platform'),
            ('Tokens', 'Token'),
            ('Token', 'Token'),
            ('every day', 'setiap hari'),
            ('Daily', 'Harian'),
        ]
        result = step
        for eng, indo in translations:
            result = result.replace(eng, indo)
        return result
    
    def _check_requires_payment(self, content, actions, steps):
        """Check if airdrop requires any payment/gas fee"""
        # Keywords that indicate payment needed
        payment_keywords = [
            'bridge', 'swap', 'stake', 'deposit', 'buy', 'purchase',
            'gas fee', 'transaction fee', 'pay', 'invest', 'mint nft',
            'sol', 'eth', 'bnb', 'matic', 'usdt', 'usdc'
        ]
        
        # Check actions text
        actions_lower = actions.lower()
        for keyword in payment_keywords:
            if keyword in actions_lower:
                return True, f"Butuh: {keyword}"
        
        # Check steps
        for step in steps:
            step_lower = step.lower()
            for keyword in payment_keywords:
                if keyword in step_lower:
                    return True, f"Step minta: {keyword}"
        
        return False, ""
    
    def scrape_airdrops_io(self):
        """Scrape airdrops.io for FREE airdrops only"""
        self._log("Scraping airdrops.io (FREE only)...")
        campaigns = []
        
        url = "https://airdrops.io"
        data = self._curl_get(url, {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})
        
        if not data:
            return campaigns
        
        article_pattern = r'<article[^>]*id="post-(\d+)"[^>]*class="[^"]*airdrop-click[^"]*"(.*?)</article>'
        articles = re.findall(article_pattern, data, re.DOTALL)
        
        for post_id, content in articles:
            name_match = re.search(r'<h3>(.*?)</h3>', content)
            if not name_match:
                continue
            name = name_match.group(1).strip()
            
            url_match = re.search(r'href="(https://airdrops\.io/[^"]+)"', content)
            link = url_match.group(1) if url_match else f"https://airdrops.io/?p={post_id}"
            
            temp_match = re.search(r'data-temperature="(\d+)"', content)
            temperature = int(temp_match.group(1)) if temp_match else 0
            
            is_confirmed = 'badge-confirmed' in content
            
            # Extract requirements
            requirements = []
            if 'telegram required' in content.lower():
                requirements.append('Telegram')
            if 'twitter required' in content.lower():
                requirements.append('Twitter/X')
            if 'email-address-required="1"' in content:
                requirements.append('Email')
            if 'kyc-required="1"' in content:
                requirements.append('KYC')
            
            # Skip if requires KYC (usually not worth it)
            if 'KYC' in requirements:
                self._log(f"Skipped {name}: requires KYC")
                continue
            
            airdrop_id = f"airdrops_{post_id}"
            if self._is_new(airdrop_id):
                # Fetch detail page for steps
                detail = self._scrape_detail(link)
                steps = detail.get('steps', [])
                actions = detail.get('actions', '')
                
                # Check if requires payment
                requires_payment, payment_reason = self._check_requires_payment(content, actions, steps)
                
                if requires_payment:
                    self._log(f"Skipped {name}: {payment_reason}")
                    continue
                
                # Only include if truly free (social tasks only)
                campaigns.append({
                    'id': airdrop_id,
                    'name': name,
                    'url': link,
                    'temperature': temperature,
                    'confirmed': is_confirmed,
                    'actions': actions,
                    'requirements': requirements,
                    'steps': steps,
                })
                self._mark_seen(airdrop_id)
        
        return campaigns
    
    def _scrape_detail(self, url):
        """Scrape detail page for step-by-step instructions"""
        detail = {'steps': [], 'actions': ''}
        
        data = self._curl_get(url, {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})
        if not data:
            return detail
        
        # Extract "How to participate" section
        howto_match = re.search(r'(?:How to participate|Cara|Steps?|Instructions?).*?<ol[^>]*>(.*?)</ol>', data, re.DOTALL | re.IGNORECASE)
        if howto_match:
            steps = re.findall(r'<li[^>]*>(.*?)</li>', howto_match.group(1), re.DOTALL)
            detail['steps'] = [self._translate_step(re.sub(r'<[^>]+>', '', s).strip()) for s in steps[:5]]
        
        # If no ol, try ul
        if not detail['steps']:
            howto_match = re.search(r'(?:How to participate|Cara|Steps?|Instructions?).*?<ul[^>]*>(.*?)</ul>', data, re.DOTALL | re.IGNORECASE)
            if howto_match:
                steps = re.findall(r'<li[^>]*>(.*?)</li>', howto_match.group(1), re.DOTALL)
                detail['steps'] = [self._translate_step(re.sub(r'<[^>]+>', '', s).strip()) for s in steps[:5]]
        
        # Extract actions text
        actions_match = re.search(r"Actions:.*?<span>(.*?)</span>", data, re.DOTALL)
        if actions_match:
            detail['actions'] = self._translate_step(re.sub(r'<[^>]+>', '', actions_match.group(1)).strip())
        
        return detail
    
    def format_message(self, campaigns):
        if not campaigns:
            return None
        
        campaigns.sort(key=lambda x: x.get('temperature', 0), reverse=True)
        
        msg = f"🎯 <b>AIRDROP GRATIS</b>\n"
        msg += f"💰 100% FREE - Gak perlu bayar apapun!\n"
        msg += f"📅 {datetime.now().strftime('%d %b %Y %H:%M')}\n"
        msg += f"{'='*30}\n\n"
        
        for c in campaigns[:5]:
            temp = c.get('temperature', 0)
            confirmed = "✅" if c.get('confirmed') else ""
            
            if temp > 100:
                emoji = '🔥🔥'
            elif temp > 50:
                emoji = '🔥'
            elif temp > 10:
                emoji = '⭐'
            else:
                emoji = '🆕'
            
            msg += f"{emoji} <b>{c['name']}</b> {confirmed}\n"
            if c.get('requirements'):
                msg += f"📌 Siapin: {', '.join(c['requirements'])}\n"
            msg += f"🔥 Heat: {temp}°\n\n"
            
            # Step-by-step
            if c.get('steps'):
                msg += f"📋 <b>Cara ikutan:</b>\n"
                for i, step in enumerate(c['steps'][:4], 1):
                    msg += f"{i}. {step}\n"
            elif c.get('actions'):
                msg += f"📋 {c['actions']}\n"
            
            msg += f"\n🔗 {c['url']}\n"
            msg += f"{'─'*30}\n\n"
        
        if len(campaigns) > 5:
            msg += f"... +{len(campaigns) - 5} airdrop gratis lainnya\n\n"
        
        msg += f"💡 <b> semua GRATIS!</b>\n"
        msg += f"⚡ Cuma butuh: akun Twitter/Telegram"
        
        return msg
    
    def run(self):
        self._log("Airdrop Hunter started!")
        
        campaigns = self.scrape_airdrops_io()
        self._log(f"Found {len(campaigns)} FREE airdrops")
        
        if campaigns:
            msg = self.format_message(campaigns)
            if msg:
                self._send_telegram(msg)
                self._log(f"Sent {len(campaigns)} airdrops")
        else:
            self._log("No new free airdrops")
        
        return campaigns

if __name__ == "__main__":
    hunter = AirdropHunter()
    hunter.run()
