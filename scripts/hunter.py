import subprocess
import json
import time
import os
import re
import csv
from datetime import datetime, timedelta
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    import pandas as pd
    HAS_PANDAS = True
except:
    HAS_PANDAS = False

# ================= CONFIG OP =================
OP_CONFIG = {
    "sources": ["airdrops_io", "airdropalert", "cryptorank"],
    "min_temperature": 0,  # 0 = semua, naikkan ke 20 untuk filter sampah
    "top_n_telegram": 5,
    "alert_hot_temp": 80,  # temp >=80 + confirmed => alert 🚨
    "seen_ttl_days": 14,
    "rate_limit_s": 1.5,
    "excel_path": "data/airdrops_OP.xlsx",
    "csv_path": "data/airdrops_OP.csv",
}

SCAM_KEYWORDS = [
    "seed phrase", "private key", "mnemonic", "approve unlimited",
    "drainer", "send your", "wallet drain", "connect to claim instantly",
    "first 100 only send"
]
PAYMENT_KEYWORDS = [
    'bridge', 'swap', 'stake', 'deposit', 'buy', 'purchase',
    'gas fee', 'transaction fee', 'pay ', 'invest', 'mint nft',
    'sol', 'eth', 'bnb', 'matic', 'usdt', 'usdc', 'fee required',
    'trade', 'trading', 'volume', 'liquidity', 'perpetual', 'futures', 'top up', 'topup'
]

class AirdropHunter:
    def __init__(self, config_override=None):
        self.config = {
            'telegram_bot_token': os.environ.get('TELEGRAM_BOT_TOKEN', ''),
            'telegram_chat_id': os.environ.get('TELEGRAM_CHAT_ID', ''),
        }
        if config_override:
            self.config.update(config_override)
        if not self.config['telegram_bot_token']:
            self._load_config_from_file()
        self.seen_file = "config/seen_airdrops.json"
        self.seen = self._load_seen()
        self.log_file = "logs/hunter.log"
        self.all_campaigns = []

    def _load_config_from_file(self):
        for p in ["config/.env", ".env", "config/config.env"]:
            if os.path.exists(p):
                with open(p, encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        line=line.strip()
                        if not line or line.startswith('#') or '=' not in line: continue
                        k,v=line.split('=',1)
                        self.config[k.strip()]=v.strip().strip('"').strip("'")

    def _load_seen(self):
        if os.path.exists(self.seen_file):
            try:
                with open(self.seen_file, encoding="utf-8") as f: return json.load(f)
            except: return {}
        return {}
    def _save_seen(self):
        os.makedirs(os.path.dirname(self.seen_file), exist_ok=True)
        with open(self.seen_file, 'w', encoding="utf-8") as f: json.dump(self.seen, f, indent=2, ensure_ascii=False)
    def _log(self, msg):
        ts=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line=f"[{ts}] {msg}"
        print(line)
        try:
            os.makedirs(os.path.dirname(self.log_file), exist_ok=True)
            with open(self.log_file, 'a', encoding="utf-8") as f: f.write(line+"\n")
        except: pass

    def _curl_get(self, url, headers=None):
        cmd=['curl','-s','-L','--max-time','30','-A','Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36']
        if headers:
            for k,v in headers.items(): cmd.extend(['-H', f'{k}: {v}'])
        cmd.append(url)
        try:
            r=subprocess.run(cmd, capture_output=True, text=True, timeout=35)
            return r.stdout if r.stdout else None
        except Exception as e:
            self._log(f"Curl error {url}: {e}")
            return None

    def _send_telegram(self, message):
        token=self.config.get('telegram_bot_token','')
        chat_id=self.config.get('telegram_chat_id','')
        if not token or not chat_id:
            self._log("Telegram not configured — print only")
            print("\n"+"="*50+f"\n{message}\n"+"="*50+"\n")
            return False
        url=f"https://api.telegram.org/bot{token}/sendMessage"
        payload=json.dumps({"chat_id":chat_id,"text":message,"parse_mode":"HTML","disable_web_page_preview":True})
        cmd=['curl','-s','-X','POST',url,'-H','Content-Type: application/json','-d',payload]
        try:
            r=subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            resp=json.loads(r.stdout) if r.stdout else {}
            ok=resp.get('ok',False)
            if not ok: self._log(f"Telegram failed: {r.stdout[:300]}")
            return ok
        except Exception as e:
            self._log(f"Telegram error: {e}")
            return False

    def _is_new(self, cid): return cid not in self.seen
    def _mark_seen(self, cid):
        self.seen[cid]=datetime.now().isoformat()
        cutoff=(datetime.now()-timedelta(days=OP_CONFIG["seen_ttl_days"])).isoformat()
        self.seen={k:v for k,v in self.seen.items() if v>cutoff}
        self._save_seen()

    # ---------- helpers ----------
    def _translate_step(self, step):
        m=[('Visit the','Kunjungi'),('Connect Your','Hubungkan'),('Solana Wallet','Wallet Solana'),('Ethereum Wallet','Wallet Ethereum'),
           ('Acquire','Dapatkan'),('Ensure you have sufficient','Pastikan kamu punya cukup'),('in your wallet for','di wallet untuk'),
           ('and transaction fees','dan biaya transaksi'),('Complete Initial Setup','Selesaikan Setup Awal'),
           ('Connect your social media accounts','Hubungkan akun media sosial kamu'),('as prompted','seperti yang diminta'),
           ('You can purchase','Kamu bisa beli'),('directly from','langsung dari'),('or use the bridge widget below','atau pakai bridge di bawah'),
           ('Bridge funds','Bridge dana'),('Follow','Follow'),('Join','Gabung'),('Telegram Group','Grup Telegram'),
           ('Discord Server','Server Discord'),('Twitter','Twitter/X'),('Like','Like'),('Retweet','Retweet'),('Submit','Kirim'),
           ('Enter','Masukkan'),('Your','Kamu'),('Address','Alamat'),('Claim','Klaim'),('Stake','Stake'),('Deposit','Deposit'),
           ('Trade','Trade'),('Swap','Swap'),('Mint','Mint'),('Tokens','Token'),('every day','setiap hari'),('Daily','Harian')]
        r=step
        for a,b in m: r=r.replace(a,b)
        return r

    def _is_scam(self, text):
        low=text.lower()
        for kw in SCAM_KEYWORDS:
            if kw in low: return True, kw
        return False, ""

    def _requires_payment(self, content, actions, steps):
        txt=(content+" "+actions+" "+" ".join(steps)).lower()
        scam, why=self._is_scam(txt)
        if scam: return True, f"SCAM Risk: {why}"
        # STRICT FREE: apapun yang butuh modal = skip
        hard_block = ['bridge','swap','stake','deposit','gas fee','transaction fee','mint nft','trade','trading','volume','liquidity','perpetual','futures','top up','topup']
        for kw in hard_block:
            if kw in txt:
                return True, f"Butuh modal: {kw}"
        # soft block untuk buy/pay/invest kalau barengan trading
        for kw in ['buy','purchase','pay ','invest','fee required']:
            if kw in txt and any(x in txt for x in ['trade','swap','bridge','stake','deposit']):
                return True, f"Butuh bayar: {kw}"
        return False, ""

    def _score(self, c):
        s=c.get('temperature',0)
        if c.get('confirmed'): s+=25
        if 'Email' in c.get('requirements',[]): s+=5  # email doang = easy
        if 'KYC' in c.get('requirements',[]): s-=100
        # penalty if no steps (info kurang)
        if not c.get('steps'): s-=5
        # freshness bonus (new id)
        s+=5
        # scam already filtered
        c['score']=s
        return s

    # ---------- scrapers ----------
    def scrape_airdrops_io(self):
        self._log("Scraping airdrops.io (FREE only)...")
        out=[]
        data=self._curl_get("https://airdrops.io", {'User-Agent':'Mozilla/5.0'})
        if not data: return out
        arts=re.findall(r'<article[^>]*id="post-(\d+)"[^>]*class="[^\"]*airdrop-click[^\"]*"(.*?)</article>', data, re.DOTALL)
        for post_id, content in arts:
            name_m=re.search(r'<h3>(.*?)</h3>', content)
            if not name_m: continue
            name=re.sub(r'<[^>]+>','',name_m.group(1)).strip()
            url_m=re.search(r'href="(https://airdrops\.io/[^\"]+)"', content)
            link=url_m.group(1) if url_m else f"https://airdrops.io/?p={post_id}"
            temp_m=re.search(r'data-temperature="(\d+)"', content)
            temp=int(temp_m.group(1)) if temp_m else 0
            if temp < OP_CONFIG["min_temperature"]: continue
            confirmed='badge-confirmed' in content
            reqs=[]
            if 'telegram required' in content.lower(): reqs.append('Telegram')
            if 'twitter required' in content.lower(): reqs.append('Twitter/X')
            if 'email-address-required="1"' in content: reqs.append('Email')
            if 'kyc-required="1"' in content: reqs.append('KYC')
            if 'KYC' in reqs:
                self._log(f"Skip {name}: KYC")
                continue
            aid=f"airdrops_{post_id}"
            if not self._is_new(aid): continue
            detail=self._scrape_detail(link)
            steps=detail.get('steps',[]); actions=detail.get('actions','')
            need, why=self._requires_payment(content, actions, steps)
            if need:
                self._log(f"Skip {name}: {why}")
                continue
            scam, _=self._is_scam(name+" "+" ".join(steps))
            if scam: continue
            c={'id':aid,'name':name,'url':link,'temperature':temp,'confirmed':confirmed,'actions':actions,'requirements':reqs,'steps':steps,'source':'airdrops.io'}
            self._score(c)
            out.append(c); self._mark_seen(aid)
            time.sleep(OP_CONFIG["rate_limit_s"])
            if len(out)>=20: break
        self._log(f"airdrops.io → {len(out)} baru")
        return out

    def scrape_airdropalert(self):
        self._log("Scraping airdropalert.com ...")
        out=[]
        data=self._curl_get("https://airdropalert.com/", {'User-Agent':'Mozilla/5.0'})
        if not data: return out
        # airdropalert uses div with data or article
        # fallback: find all /airdrops/ links
        links=re.findall(r'href="(https://airdropalert\.com/airdrops/[^"]+)"', data)
        links=list(dict.fromkeys(links))[:12]
        for link in links:
            # name from url slug
            slug=link.rstrip('/').split('/')[-1].replace('-',' ').title()
            aid=f"alert_{re.sub(r'[^a-z0-9]','',slug.lower())}"
            if not self._is_new(aid): continue
            detail=self._scrape_detail_generic(link)
            steps=detail.get('steps',[]); actions=detail.get('actions','')
            need, why=self._requires_payment(slug, actions, steps)
            if need: continue
            c={'id':aid,'name':slug,'url':link,'temperature':30,'confirmed':False,'actions':actions,'requirements':[],'steps':steps,'source':'airdropalert.com'}
            self._score(c)
            out.append(c); self._mark_seen(aid)
            time.sleep(OP_CONFIG["rate_limit_s"])
        self._log(f"airdropalert → {len(out)} baru")
        return out

    def scrape_cryptorank(self):
        self._log("Scraping cryptorank.io/drophunting ...")
        out=[]
        data=self._curl_get("https://cryptorank.io/drophunting", {'User-Agent':'Mozilla/5.0'})
        if not data: return out
        # find drop links
        links=re.findall(r'href="(/drophunting/[^"]+)"', data)
        links=list(dict.fromkeys(links))[:10]
        for p in links:
            link="https://cryptorank.io"+p
            slug=p.strip('/').split('/')[-1].replace('-',' ').title()
            aid=f"cr_{re.sub(r'[^a-z0-9]','',slug.lower())}"
            if not self._is_new(aid): continue
            detail=self._scrape_detail_generic(link)
            c={'id':aid,'name':slug,'url':link,'temperature':20,'confirmed':False,'actions':detail.get('actions',''),'requirements':[],'steps':detail.get('steps',[]),'source':'cryptorank.io'}
            self._score(c)
            out.append(c); self._mark_seen(aid)
            time.sleep(OP_CONFIG["rate_limit_s"])
        self._log(f"cryptorank → {len(out)} baru")
        return out

    def _scrape_detail(self, url):
        d={'steps':[],'actions':''}
        data=self._curl_get(url, {'User-Agent':'Mozilla/5.0'})
        if not data: return d
        # 1) JSON-LD HowTo (paling bersih - airdrops.io pakai ini)
        try:
            for jm in re.findall(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', data, re.DOTALL):
                try: j=json.loads(jm)
                except: continue
                cands=[]
                if isinstance(j, dict) and '@graph' in j: cands=j['@graph']
                elif isinstance(j, list): cands=j
                else: cands=[j]
                for node in cands:
                    if not isinstance(node, dict): continue
                    # cek HowTo langsung
                    howtos=[]
                    if node.get('@type')=='HowTo' and 'step' in node: howtos.append(node)
                    for subj in node.get('subjectOf',[]) if isinstance(node.get('subjectOf'), list) else []:
                        if isinstance(subj, dict) and subj.get('@type')=='HowTo': howtos.append(subj)
                    for hw in howtos:
                        cleaned=[]
                        for s in hw.get('step',[]):
                            if isinstance(s, dict):
                                t=(s.get('text') or s.get('name') or '').strip()
                                t=re.sub(r'<[^>]+>','',t).strip()
                                if t and len(t)>10 and 'Airdrop Is Almost Here' not in t and t.upper()!='JOIN NOW':
                                    cleaned.append(self._translate_step(t))
                        if cleaned:
                            d['steps']=cleaned[:6]
                            return d
        except Exception as e:
            self._log(f"JSON-LD fail {url[:40]}: {e}")
        # 2) fallback ol/ul
        m=re.search(r'(?:How to participate|Cara|Steps?|Instructions?).*?<ol[^>]*>(.*?)</ol>', data, re.DOTALL|re.IGNORECASE)
        if m:
            steps=re.findall(r'<li[^>]*>(.*?)</li>', m.group(1), re.DOTALL)
            cand=[self._translate_step(re.sub(r'<[^>]+>','',s).strip()) for s in steps[:6] if s.strip()]
            cand=[c for c in cand if 'Airdrop Is Almost Here' not in c and c.upper()!='JOIN NOW' and len(c)>12]
            if cand: d['steps']=cand
        if not d['steps']:
            m=re.search(r'(?:How to participate|Cara|Steps?|Instructions?).*?<ul[^>]*>(.*?)</ul>', data, re.DOTALL|re.IGNORECASE)
            if m:
                steps=re.findall(r'<li[^>]*>(.*?)</li>', m.group(1), re.DOTALL)
                cand=[self._translate_step(re.sub(r'<[^>]+>','',s).strip()) for s in steps[:6] if s.strip()]
                cand=[c for c in cand if 'Airdrop Is Almost Here' not in c and len(c)>12]
                if cand: d['steps']=cand
        am=re.search(r"Actions:.*?<span>(.*?)</span>", data, re.DOTALL)
        if am: d['actions']=self._translate_step(re.sub(r'<[^>]+>','',am.group(1)).strip())
        return d

    def _scrape_detail_generic(self, url):
        d={'steps':[],'actions':''}
        data=self._curl_get(url, {'User-Agent':'Mozilla/5.0'})
        if not data: return d
        # generic ol/ul first 5 li
        m=re.search(r'<ol[^>]*>(.*?)</ol>', data, re.DOTALL)
        if not m: m=re.search(r'<ul[^>]*>(.*?)</ul>', data, re.DOTALL)
        if m:
            steps=re.findall(r'<li[^>]*>(.*?)</li>', m.group(1), re.DOTALL)
            d['steps']=[self._translate_step(re.sub(r'<[^>]+>','',s).strip()) for s in steps[:5] if s.strip()]
        return d

    # ---------- export + format ----------
    def _export(self, campaigns):
        if not campaigns: return
        os.makedirs("data", exist_ok=True)
        # CSV always
        try:
            with open(OP_CONFIG["csv_path"], 'w', newline='', encoding='utf-8-sig') as f:
                w=csv.DictWriter(f, fieldnames=["score","name","temperature","confirmed","requirements","steps","url","source"])
                w.writeheader()
                for c in campaigns:
                    w.writerow({"score":c.get('score',0),"name":c['name'],"temperature":c.get('temperature',0),
                                "confirmed":"YA" if c.get('confirmed') else "","requirements":",".join(c.get('requirements',[])),
                                "steps":" | ".join(c.get('steps',[][:120])),"url":c['url'],"source":c['source']})
            self._log(f"CSV → {OP_CONFIG['csv_path']}")
        except Exception as e: self._log(f"CSV fail: {e}")
        if HAS_PANDAS:
            try:
                df=pd.DataFrame([{"Score":c.get('score',0),"Nama":c['name'],"Heat":c.get('temperature',0),"Confirmed":c.get('confirmed'),
                                   "Syarat":",".join(c.get('requirements',[])),"Cara":" | ".join(c.get('steps',[])),"Link":c['url'],"Sumber":c['source']} for c in campaigns])
                df=df.sort_values("Score", ascending=False)
                df.to_excel(OP_CONFIG["excel_path"], index=False)
                self._log(f"Excel → {OP_CONFIG['excel_path']}")
            except Exception as e: self._log(f"Excel fail: {e}")

    def format_message(self, campaigns):
        if not campaigns: return None
        campaigns=sorted(campaigns, key=lambda x: x.get('score',0), reverse=True)
        hot=[c for c in campaigns if c.get('temperature',0)>=OP_CONFIG["alert_hot_temp"] and c.get('confirmed')]
        header="\U0001f6a8 <b>HOT AIRDROP</b> \U0001f6a8\n" if hot else "\U0001f3af <b>AIRDROP GRATIS - OP</b>\n"
        msg=header
        msg+=f"\U0001f4c5 {datetime.now().strftime('%d %b %Y %H:%M WIB')} - {len(campaigns)} baru (FREE, no KYC, no bayar)\n"
        msg+=f"{'='*30}\n\n"
        for c in campaigns[:OP_CONFIG["top_n_telegram"]]:
            temp=c.get('temperature',0); score=c.get('score',0)
            confirmed=" CONFIRMED" if c.get('confirmed') else " (speculative)"
            if temp>=150: emoji='\U0001f525\U0001f525'
            elif temp>=80: emoji='\U0001f525'
            elif temp>=30: emoji='\u2b50'
            else: emoji='\U0001f195'
            steps=c.get('steps',[])
            if len(steps)<=3 and not c.get('requirements'): est="~2 menit"
            elif len(steps)<=5: est="~5-10 menit"
            else: est="~10-15 menit"
            msg+=f"{emoji} <b>{c['name']}</b>{confirmed}\n"
            msg+=f"Heat:{temp} - Score:{score} - {est} - {c.get('source','')}\n"
            if c.get('requirements'): msg+=f"\U0001f4cc Syarat: {', '.join(c['requirements'])} (siapin dulu)\n"
            else: msg+=f"\U0001f4cc Syarat: cuma Sosmed (Follow/Join)\n"
            if steps:
                msg+=f"\U0001f4cb Cara (ringkas):\n"
                for i,s in enumerate(steps[:3],1):
                    ss=s[:85] + ("..." if len(s)>85 else "")
                    msg+=f" {i}. {ss}\n"
                if len(steps)>3: msg+=f"   +{len(steps)-3} langkah lagi di link\n"
            elif c.get('actions'): msg+=f"\U0001f4cb {c['actions'][:110]}\n"
            else: msg+=f"\U0001f4cb Buka link -> ikuti panduan di halaman\n"
            msg+=f"\U0001f517 {c['url']}\n"
            msg+=f"\U0001f4a1 Gratis - jangan deposit/bridge/swap\n"
            msg+=f"{'─'*28}\n\n"
        if len(campaigns)>OP_CONFIG["top_n_telegram"]:
            msg+=f"... +{len(campaigns)-OP_CONFIG['top_n_telegram']} lagi lengkap di Excel\n\n"
        msg+=f"\U0001f4ca File: <code>{OP_CONFIG['excel_path']}</code> (buka di HP/PC)\n"
        msg+=f"\u26a0\ufe0f Selalu cek: kalau diminta seed phrase / kirim uang = SCAM, skip!"
        return msg

    def run(self, dry_run=False):
        self._log("Airdrop Hunter OP started! sources=%s" % ",".join(OP_CONFIG["sources"]))
        all_camps=[]
        # parallel fetch
        with ThreadPoolExecutor(max_workers=3) as ex:
            futs={}
            if "airdrops_io" in OP_CONFIG["sources"]: futs[ex.submit(self.scrape_airdrops_io)]="airdrops_io"
            if "airdropalert" in OP_CONFIG["sources"]: futs[ex.submit(self.scrape_airdropalert)]="airdropalert"
            if "cryptorank" in OP_CONFIG["sources"]: futs[ex.submit(self.scrape_cryptorank)]="cryptorank"
            for fut in as_completed(futs):
                try: all_camps.extend(fut.result() or [])
                except Exception as e: self._log(f"Source {futs[fut]} error: {e}")
        # dedupe by url
        seen_url={}; uniq=[]
        for c in all_camps:
            if c['url'] not in seen_url:
                seen_url[c['url']]=True; uniq.append(c)
        uniq=sorted(uniq, key=lambda x: x.get('score',0), reverse=True)
        self._log(f"Total baru (dedupe): {len(uniq)}")
        if uniq:
            self._export(uniq)
            msg=self.format_message(uniq)
            if msg and not dry_run:
                self._send_telegram(msg)
                self._log(f"Sent {min(len(uniq), OP_CONFIG['top_n_telegram'])} to Telegram")
            elif dry_run:
                self._log("DRY RUN — tidak kirim Telegram")
                print(msg or "(no msg)")
        else:
            self._log("No new free airdrops (semua sudah seen atau terfilter)")
        return uniq

if __name__=="__main__":
    ap=argparse.ArgumentParser(description="Airdrop Hunter OP")
    ap.add_argument("--dry-run", action="store_true", help="jangan kirim Telegram, cuma print + export")
    ap.add_argument("--sources", nargs="*", help="override sources, ex: --sources airdrops_io")
    args=ap.parse_args()
    if args.sources: OP_CONFIG["sources"]=args.sources
    hunter=AirdropHunter()
    hunter.run(dry_run=args.dry_run)
