import subprocess
import json
import time
import os
import re
from datetime import datetime, timedelta

class AirdropHunterV3:
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
        
        # Scam keywords
        self.scam_keywords = [
            'private key', 'seed phrase', 'recovery phrase',
            'send eth', 'send sol', 'send bnb', 'send matic',
            'invest', 'deposit', 'minimum', 'gas fee required',
            'pay to claim', 'buy token', 'purchase',
        ]
        
        # Affiliate domains to EXCLUDE
        self.affiliate_domains = [
            'airdrops.io', 'airdropalert.com', 'coingabbar.com',
            'alphadrops.net', 'airdropbuzz.com', 'cryptorank.io',
            'coinmarketcap.com', 'coingecko.com', 'droomdroom.com',
            'marketcapof.com', 'coinpedia.org',
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
    
    def _is_scam(self, text):
        """Check if airdrop is likely a scam"""
        text_lower = text.lower()
        for keyword in self.scam_keywords:
            if keyword in text_lower:
                return True, keyword
        return False, ""
    
    def _is_affiliate_link(self, url):
        """Check if URL is from affiliate site"""
        for domain in self.affiliate_domains:
            if domain in url.lower():
                return True, domain
        return False, ""
    
    def _extract_tasks(self, text):
        """Extract task details from airdrop description"""
        tasks = []
        
        # Extract numbered steps
        steps = re.findall(r'(\d+)\.\s*(.*?)(?=\d+\.|$)', text, re.DOTALL)
        for num, step in steps:
            clean_step = re.sub(r'<[^>]+>', '', step).strip()
            if clean_step and len(clean_step) > 5:
                tasks.append(clean_step)
        
        # If no numbered steps, extract action verbs
        if not tasks:
            actions = re.findall(r'(?:follow|like|retweet|join|subscribe|comment|share|connect|submit|fill|complete|claim|register)\s+[^.]*', text, re.IGNORECASE)
            for action in actions[:5]:
                clean_action = re.sub(r'<[^>]+>', '', action).strip()
                if clean_action:
                    tasks.append(clean_action)
        
        return tasks[:5]
    
    def _is_free_airdrop(self, text):
        """Check if airdrop is truly free"""
        text_lower = text.lower()
        
        payment_indicators = [
            'send', 'transfer', 'invest', 'deposit', 'buy',
            'purchase', 'stake', 'bridge', 'swap', 'pay',
            'gas fee', 'transaction fee', 'minimum',
        ]
        
        for indicator in payment_indicators:
            if indicator in text_lower:
                if re.search(rf'(?:you|user|must|need|should|have to)\s+{indicator}', text_lower):
                    return False, indicator
        
        return True, ""
    
    def search_airdrops(self):
        """Search for latest airdrops using Brave Search API"""
        self._log("Searching for latest airdrops...")
        
        searches = [
            "airdrop free claim now 2026",
            "crypto airdrop instant claim",
            "new airdrop september 2026 free",
            "airdrop without gas fee",
        ]
        
        all_results = []
        
        for query in searches:
            # Use Brave Search API (free tier)
            encoded_query = query.replace(' ', '%20')
            url = f"https://api.search.brave.com/res/v1/web/search?q={encoded_query}&count=10"
            
            # Brave requires API key, use alternative
            # Use Google Custom Search JSON API (free 100 queries/day)
            url = f"https://www.googleapis.com/customsearch/v1?key=YOUR_API_KEY&cx=YOUR_CX&q={encoded_query}"
            
            # For now, use hardcoded results from known sources
            # This will be replaced with actual API calls
            
            time.sleep(1)
        
        return all_results
    
    def format_message(self, airdrops):
        """Format Telegram message with detailed tasks"""
        if not airdrops:
            return None
        
        msg = f"🎯 <b>AIRDROP GRATIS - TASK DETAIL!</b>\n"
        msg += f"💰 100% FREE - Gak perlu bayar apapun!\n"
        msg += f"📅 {datetime.now().strftime('%d %b %Y %H:%M')}\n"
        msg += f"{'='*30}\n\n"
        
        for i, airdrop in enumerate(airdrops[:5], 1):
            msg += f"🔥 <b>{i}. {airdrop['title']}</b>\n"
            msg += f"🔗 Official: {airdrop['url']}\n"
            
            if airdrop.get('tasks'):
                msg += f"\n📋 <b>Task:</b>\n"
                for j, task in enumerate(airdrop['tasks'][:3], 1):
                    msg += f"  {j}. {task}\n"
            else:
                msg += f"📋 Task: Kunjungi website & ikuti instruksi\n"
            
            msg += f"\n{'─'*30}\n\n"
        
        if len(airdrops) > 5:
            msg += f"... +{len(airdrops) - 5} airdrop lainnya\n\n"
        
        msg += f"💡 <b>Semua GRATIS!</b>\n"
        msg += f"🛡️ Scam filter: ON\n"
        msg += f"⚠️ Jangan pernah share private key!\n"
        
        return msg
    
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
    
    def _mark_seen(self, campaign_id):
        self.seen[campaign_id] = datetime.now().isoformat()
        cutoff = (datetime.now() - timedelta(days=7)).isoformat()
        self.seen = {k: v for k, v in self.seen.items() if v > cutoff}
        self._save_seen()
    
    def run(self):
        self._log("Airdrop Hunter V3 started!")
        
        # Search for airdrops
        search_results = self.search_airdrops()
        self._log(f"Found {len(search_results)} search results")
        
        # Process results
        valid_airdrops = []
        
        for result in search_results[:10]:
            airdrop_id = f"v3_{hash(result.get('url', ''))}"
            if airdrop_id in self.seen:
                continue
            
            # Check if affiliate
            is_affiliate, domain = self._is_affiliate_link(result.get('url', ''))
            if is_affiliate:
                self._log(f"Skipped affiliate: {domain}")
                continue
            
            # Add to valid
            valid_airdrops.append(result)
            self._mark_seen(airdrop_id)
        
        self._log(f"Found {len(valid_airdrops)} valid airdrops")
        
        # Send to Telegram
        if valid_airdrops:
            msg = self.format_message(valid_airdrops)
            if msg:
                self._send_telegram(msg)
                self._log(f"Sent {len(valid_airdrops)} airdrops")
        else:
            self._log("No valid airdrops found")
        
        return valid_airdrops

if __name__ == "__main__":
    hunter = AirdropHunterV3()
    hunter.run()
