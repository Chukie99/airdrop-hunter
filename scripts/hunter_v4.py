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
        
        self.scam_keywords = [
            'private key', 'seed phrase', 'recovery phrase',
            'send eth', 'send sol', 'send bnb', 'send matic',
            'invest', 'deposit', 'minimum', 'gas fee required',
            'pay to claim', 'buy token', 'purchase',
        ]
        
        self.affiliate_domains = [
            'airdrops.io', 'airdropalert.com', 'coingabbar.com',
            'alphadrops.net', 'airdropbuzz.com', 'cryptorank.io',
            'coinmarketcap.com', 'coingecko.com', 'droomdroom.com',
            'marketcapof.com', 'coinpedia.org',
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
    
    def _is_scam(self, text):
        text_lower = text.lower()
        for keyword in self.scam_keywords:
            if keyword in text_lower:
                return True, keyword
        return False, ""
    
    def _is_affiliate_link(self, url):
        for domain in self.affiliate_domains:
            if domain in url.lower():
                return True, domain
        return False, ""
    
    def _is_free_airdrop(self, text):
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
    
    def _curl_get(self, url, headers=None):
        cmd = ['curl', '-s', '-L', '--max-time', '15', '--insecure']
        if headers:
            for k, v in headers.items():
                cmd.extend(['-H', f'{k}: {v}'])
        cmd.append(url)
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
            return result.stdout
        except:
            return None
    
    def search_google_news(self):
        self._log("Searching Google News RSS...")
        
        queries = [
            "crypto airdrop free claim",
            "new airdrop september 2026",
            "free token airdrop",
        ]
        
        all_results = []
        
        for query in queries:
            encoded = query.replace(' ', '+')
            url = f"https://news.google.com/rss/search?q={encoded}+airdrop&hl=en-US&gl=US&ceid=US:en"
            
            html = self._curl_get(url)
            if not html:
                continue
            
            items = re.findall(r'<item>(.*?)</item>', html, re.DOTALL)
            
            for item in items:
                title_match = re.search(r'<title>(.*?)</title>', item)
                link_match = re.search(r'<link/>(.*?)(?:\n|<)', item)
                if not link_match:
                    link_match = re.search(r'<link>(.*?)</link>', item)
                desc_match = re.search(r'<description>(.*?)</description>', item, re.DOTALL)
                
                if title_match:
                    title = re.sub(r'<!\[CDATA\[(.*?)\]\]>', r'\1', title_match.group(1)).strip()
                    link = link_match.group(1).strip() if link_match else ""
                    desc = re.sub(r'<!\[CDATA\[(.*?)\]\]>', r'\1', desc_match.group(1)).strip() if desc_match else ""
                    desc = re.sub(r'<[^>]+>', '', desc).strip()
                    
                    is_affiliate, domain = self._is_affiliate_link(link)
                    if is_affiliate:
                        continue
                    
                    if not any(x in (title + desc).lower() for x in ['airdrop', 'free', 'claim', 'token']):
                        continue
                    
                    all_results.append({
                        'title': title,
                        'url': link,
                        'description': desc[:200],
                    })
        
        return all_results
    
    def format_message(self, airdrops):
        if not airdrops:
            return None
        
        msg = "REKOMENDASI HARI INI\n"
        msg += "==============================\n\n"
        
        for i, airdrop in enumerate(airdrops[:3], 1):
            msg += f"{i}. {airdrop['title'][:60]}\n"
            msg += f"Link: {airdrop['url']}\n"
            
            if airdrop.get('description'):
                msg += f"Detail: {airdrop['description'][:100]}\n"
            
            msg += "\n---\n\n"
        
        msg += "==============================\n"
        msg += "100% GRATIS!\n"
        msg += "Jangan kasih seed phrase = SCAM!\n"
        
        return msg
    
    def _send_telegram(self, message):
        if not self.telegram_bot_token:
            self._log("Telegram not configured")
            print(f"\n{'='*50}\n{message}\n{'='*50}\n")
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
    
    def _mark_seen(self, campaign_id):
        self.seen[campaign_id] = datetime.now().isoformat()
        cutoff = (datetime.now() - timedelta(days=7)).isoformat()
        self.seen = {k: v for k, v in self.seen.items() if v > cutoff}
        self._save_seen()
    
    def run(self):
        self._log("Airdrop Hunter V4 started!")
        
        results = self.search_google_news()
        self._log(f"Found {len(results)} results")
        
        valid_airdrops = []
        
        for result in results[:15]:
            url = result['url']
            
            is_affiliate, _ = self._is_affiliate_link(url)
            if is_affiliate:
                continue
            
            is_scam, _ = self._is_scam(result.get('description', ''))
            if is_scam:
                continue
            
            is_free, _ = self._is_free_airdrop(result.get('description', ''))
            if not is_free:
                continue
            
            airdrop_id = f"news_{hash(url)}"
            if airdrop_id in self.seen:
                continue
            
            valid_airdrops.append(result)
            self._mark_seen(airdrop_id)
        
        self._log(f"Found {len(valid_airdrops)} valid airdrops")
        
        if valid_airdrops:
            msg = self.format_message(valid_airdrops)
            if msg:
                success = self._send_telegram(msg)
                self._log(f"Sent {len(valid_airdrops)} airdrops - OK: {success}")
        else:
            self._log("No valid airdrops found")
        
        return valid_airdrops

if __name__ == "__main__":
    hunter = AirdropHunterV4()
    hunter.run()
