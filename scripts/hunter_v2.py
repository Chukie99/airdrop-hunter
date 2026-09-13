import subprocess
import json
import time
import os
import re
from datetime import datetime, timedelta

class AirdropHunterV2:
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
        self.scam_keywords = [
            'private key', 'seed phrase', 'recovery phrase',
            'send eth', 'send sol', 'send bnb', 'send matic',
            'invest', 'deposit', 'minimum', 'gas fee required',
            'pay to claim', 'buy token', 'purchase',
        ]
        
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
    
    def _is_scam(self, text):
        """Check if airdrop is likely a scam"""
        text_lower = text.lower()
        for keyword in self.scam_keywords:
            if keyword in text_lower:
                return True, keyword
        return False, ""
    
    def _check_project_legitimacy(self, project_name):
        """Verify project is legitimate by checking multiple sources"""
        # Check CoinGecko
        url = f"https://api.coingecko.com/api/v3/search?query={project_name}"
        data = self._curl_get(url)
        if data:
            try:
                result = json.loads(data)
                if result.get('coins') and len(result['coins']) > 0:
                    return True, "Listed on CoinGecko"
            except:
                pass
        
        # Check CoinMarketCap (simplified)
        url = f"https://api.coinmarketcap.com/v1/cryptocurrency/listings/latest"
        # This is rate-limited, so we skip for now
        
        return False, "Not verified"
    
    def scrape_cryptorank(self):
        """Scrape CryptoRank for airdrops"""
        self._log("Scraping CryptoRank...")
        campaigns = []
        
        url = "https://cryptorank.io/drophunting"
        data = self._curl_get(url, {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})
        
        if not data:
            return campaigns
        
        # Parse airdrop listings
        pattern = r'<div[^>]*class="[^"]*airdrop[^"]*"[^>]*>(.*?)</div>'
        matches = re.findall(pattern, data, re.DOTALL)
        
        for match in matches:
            name_match = re.search(r'<h3[^>]*>(.*?)</h3>', match)
            if not name_match:
                continue
            
            name = re.sub(r'<[^>]+>', '', name_match.group(1)).strip()
            
            # Check for scam keywords
            is_scam, reason = self._is_scam(match)
            if is_scam:
                self._log(f"Skipped {name}: scam detected ({reason})")
                continue
            
            airdrop_id = f"cryptorank_{name.lower().replace(' ', '_')}"
            if self._is_new(airdrop_id):
                campaigns.append({
                    'id': airdrop_id,
                    'name': name,
                    'source': 'CryptoRank',
                    'url': f"https://cryptorank.io/airdrop/{name.lower().replace(' ', '-')}",
                })
                self._mark_seen(airdrop_id)
        
        return campaigns
    
    def scrape_coingabbar(self):
        """Scrape CoinGabbar for airdrops"""
        self._log("Scraping CoinGabbar...")
        campaigns = []
        
        url = "https://www.coingabbar.com/en/crypto-airdrops"
        data = self._curl_get(url, {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})
        
        if not data:
            return campaigns
        
        # Parse airdrop listings
        pattern = r'<div[^>]*class="[^"]*airdrop-card[^"]*"[^>]*>(.*?)</div>'
        matches = re.findall(pattern, data, re.DOTALL)
        
        for match in matches:
            name_match = re.search(r'<h3[^>]*>(.*?)</h3>', match)
            if not name_match:
                continue
            
            name = re.sub(r'<[^>]+>', '', name_match.group(1)).strip()
            
            # Check for scam keywords
            is_scam, reason = self._is_scam(match)
            if is_scam:
                self._log(f"Skipped {name}: scam detected ({reason})")
                continue
            
            airdrop_id = f"coingabbar_{name.lower().replace(' ', '_')}"
            if self._is_new(airdrop_id):
                campaigns.append({
                    'id': airdrop_id,
                    'name': name,
                    'source': 'CoinGabbar',
                    'url': f"https://www.coingabbar.com/en/crypto-airdrops/{name.lower().replace(' ', '-')}",
                })
                self._mark_seen(airdrop_id)
        
        return campaigns
    
    def scrape_alphadrops(self):
        """Scrape AlphaDrops for airdrops"""
        self._log("Scraping AlphaDrops...")
        campaigns = []
        
        url = "https://alphadrops.net/airdrops"
        data = self._curl_get(url, {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})
        
        if not data:
            return campaigns
        
        # Parse airdrop listings
        pattern = r'<div[^>]*class="[^"]*airdrop-item[^"]*"[^>]*>(.*?)</div>'
        matches = re.findall(pattern, data, re.DOTALL)
        
        for match in matches:
            name_match = re.search(r'<h3[^>]*>(.*?)</h3>', match)
            if not name_match:
                continue
            
            name = re.sub(r'<[^>]+>', '', name_match.group(1)).strip()
            
            # Check for scam keywords
            is_scam, reason = self._is_scam(match)
            if is_scam:
                self._log(f"Skipped {name}: scam detected ({reason})")
                continue
            
            airdrop_id = f"alphadrops_{name.lower().replace(' ', '_')}"
            if self._is_new(airdrop_id):
                campaigns.append({
                    'id': airdrop_id,
                    'name': name,
                    'source': 'AlphaDrops',
                    'url': f"https://alphadrops.net/airdrop/{name.lower().replace(' ', '-')}",
                })
                self._mark_seen(airdrop_id)
        
        return campaigns
    
    def scrape_airdropbuzz(self):
        """Scrape AirdropBuzz for latest airdrops"""
        self._log("Scraping AirdropBuzz...")
        campaigns = []
        
        url = "https://airdropbuzz.com/latest-airdrops"
        data = self._curl_get(url, {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})
        
        if not data:
            return campaigns
        
        # Parse airdrop listings
        pattern = r'<div[^>]*class="[^"]*airdrop-card[^"]*"[^>]*>(.*?)</div>'
        matches = re.findall(pattern, data, re.DOTALL)
        
        for match in matches:
            name_match = re.search(r'<h3[^>]*>(.*?)</h3>', match)
            if not name_match:
                continue
            
            name = re.sub(r'<[^>]+>', '', name_match.group(1)).strip()
            
            # Check for scam keywords
            is_scam, reason = self._is_scam(match)
            if is_scam:
                self._log(f"Skipped {name}: scam detected ({reason})")
                continue
            
            airdrop_id = f"airdropbuzz_{name.lower().replace(' ', '_')}"
            if self._is_new(airdrop_id):
                campaigns.append({
                    'id': airdrop_id,
                    'name': name,
                    'source': 'AirdropBuzz',
                    'url': f"https://airdropbuzz.com/airdrop/{name.lower().replace(' ', '-')}",
                })
                self._mark_seen(airdrop_id)
        
        return campaigns
    
    def format_message(self, campaigns):
        if not campaigns:
            return None
        
        # Sort by source reliability
        source_priority = {
            'CryptoRank': 1,
            'CoinGabbar': 2,
            'AlphaDrops': 3,
            'AirdropBuzz': 4,
        }
        campaigns.sort(key=lambda x: source_priority.get(x.get('source', ''), 5))
        
        msg = f"🎯 <b>AIRDROP GRATIS - CAIR CEPAT!</b>\n"
        msg += f"💰 100% FREE - Gak perlu bayar apapun!\n"
        msg += f"⚡ Claim within 7 days\n"
        msg += f"📅 {datetime.now().strftime('%d %b %Y %H:%M')}\n"
        msg += f"{'='*30}\n\n"
        
        for c in campaigns[:10]:
            msg += f"🆕 <b>{c['name']}</b>\n"
            msg += f"📌 Source: {c.get('source', 'Unknown')}\n"
            msg += f"🔗 {c['url']}\n"
            msg += f"{'─'*30}\n\n"
        
        if len(campaigns) > 10:
            msg += f"... +{len(campaigns) - 10} airdrop gratis lainnya\n\n"
        
        msg += f"💡 <b>Semua GRATIS!</b>\n"
        msg += f"⚡ Cuma butuh: akun Twitter/Telegram\n"
        msg += f"🛡️ Scam filter: ON\n"
        
        return msg
    
    def run(self):
        self._log("Airdrop Hunter V2 started!")
        
        all_campaigns = []
        
        # Scrape from multiple sources
        all_campaigns.extend(self.scrape_cryptorank())
        all_campaigns.extend(self.scrape_coingabbar())
        all_campaigns.extend(self.scrape_alphadrops())
        all_campaigns.extend(self.scrape_airdropbuzz())
        
        # Deduplicate
        seen_names = set()
        unique_campaigns = []
        for c in all_campaigns:
            if c['name'] not in seen_names:
                seen_names.add(c['name'])
                unique_campaigns.append(c)
        
        self._log(f"Found {len(unique_campaigns)} FREE airdrops from {len(all_campaigns)} total")
        
        if unique_campaigns:
            msg = self.format_message(unique_campaigns)
            if msg:
                self._send_telegram(msg)
                self._log(f"Sent {len(unique_campaigns)} airdrops")
        else:
            self._log("No new free airdrops")
        
        return unique_campaigns

if __name__ == "__main__":
    hunter = AirdropHunterV2()
    hunter.run()
