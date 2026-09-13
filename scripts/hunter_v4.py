import requests
import json
import os
import re
from datetime import datetime, timedelta

class AirdropHunterV4:
    def __init__(self):
        self.telegram_bot_token = os.environ.get('TELEGRAM_BOT_TOKEN', '')
        self.telegram_chat_id = os.environ.get('TELEGRAM_CHAT_ID', '')
        self.seen_file = "config/seen_airdrops.json"
        self.seen = self._load_seen()
        
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
    
    def _extract_tasks(self, text):
        tasks = []
        steps = re.findall(r'(\d+)\.\s*(.*?)(?=\d+\.|$)', text, re.DOTALL)
        for num, step in steps:
            clean_step = re.sub(r'<[^>]+>', '', step).strip()
            if clean_step and len(clean_step) > 5:
                tasks.append(clean_step)
        
        if not tasks:
            actions = re.findall(r'(?:follow|like|retweet|join|subscribe|comment|share|connect|submit|fill|complete|claim|register)\s+[^.]*', text, re.IGNORECASE)
            for action in actions[:5]:
                clean_action = re.sub(r'<[^>]+>', '', action).strip()
                if clean_action:
                    tasks.append(clean_action)
        
        return tasks[:5]
    
    def scrape_airdrops_from_rss(self):
        """Scrape airdrops from RSS feeds"""
        self._log("Scraping RSS feeds...")
        
        rss_feeds = [
            "https://airdrops.io/feed/",
            "https://cryptorank.io/feed/airdrops",
            "https://coingabbar.com/feed/airdrops",
        ]
        
        all_airdrops = []
        
        for feed_url in rss_feeds:
            try:
                response = requests.get(feed_url, timeout=15, headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                })
                
                if response.status_code == 200:
                    # Parse RSS manually
                    items = re.findall(r'<item>(.*?)</item>', response.text, re.DOTALL)
                    
                    for item in items[:10]:
                        title_match = re.search(r'<title>(.*?)</title>', item)
                        link_match = re.search(r'<link>(.*?)</link>', item)
                        desc_match = re.search(r'<description>(.*?)</description>', item, re.DOTALL)
                        
                        if title_match and link_match:
                            title = re.sub(r'<!\[CDATA\[(.*?)\]\]>', r'\1', title_match.group(1)).strip()
                            link = link_match.group(1).strip()
                            desc = re.sub(r'<!\[CDATA\[(.*?)\]\]>', r'\1', desc_match.group(1)).strip() if desc_match else ""
                            
                            # Skip affiliate links
                            is_affiliate, domain = self._is_affiliate_link(link)
                            if is_affiliate:
                                continue
                            
                            # Check for scam
                            is_scam, keyword = self._is_scam(desc)
                            if is_scam:
                                continue
                            
                            # Check if free
                            is_free, reason = self._is_free_airdrop(desc)
                            if not is_free:
                                continue
                            
                            # Extract tasks
                            tasks = self._extract_tasks(desc)
                            
                            all_airdrops.append({
                                'title': title,
                                'url': link,
                                'tasks': tasks,
                                'source': 'RSS',
                            })
            except Exception as e:
                self._log(f"Error fetching {feed_url}: {e}")
        
        return all_airdrops
    
    def scrape_airdrops_from_api(self):
        """Scrape airdrops from public APIs"""
        self._log("Scraping APIs...")
        
        all_airdrops = []
        
        # CoinGecko airdrops (if available)
        try:
            # This is a placeholder - actual API may vary
            pass
        except:
            pass
        
        return all_airdrops
    
    def format_message(self, airdrops):
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
        if not self.telegram_bot_token:
            self._log("Telegram not configured")
            print(f"\n{'='*50}\n{message}\n{'='*50}\n")
            return False
        
        url = f"https://api.telegram.org/bot{self.telegram_bot_token}/sendMessage"
        payload = {
            "chat_id": self.telegram_chat_id,
            "text": message,
            "parse_mode": "HTML",
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
        
        # Scrape from multiple sources
        all_airdrops = []
        all_airdrops.extend(self.scrape_airdrops_from_rss())
        all_airdrops.extend(self.scrape_airdrops_from_api())
        
        # Deduplicate and filter
        valid_airdrops = []
        seen_urls = set()
        
        for airdrop in all_airdrops:
            url = airdrop['url']
            
            # Skip if already seen
            if url in seen_urls:
                continue
            seen_urls.add(url)
            
            # Skip if already in seen list
            airdrop_id = f"v4_{hash(url)}"
            if airdrop_id in self.seen:
                continue
            
            valid_airdrops.append(airdrop)
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
    hunter = AirdropHunterV4()
    hunter.run()
