# Airdrop Hunter — OP (Over Power)

> Hunter gratis 100% FREE — anti KYC, anti bayar, anti drainer. Multi-source + scoring + Telegram + Excel.

## Fitur OP v2
- **Multi-source**: `airdrops.io` + `airdropalert.com` + `cryptorank.io` (parallel ThreadPool)
- **Scoring**: `temperature + confirmed(+25) + anti-KYC + steps` → ranking, hot alert jika `temp≥80 & confirmed`
- **Filter OP**: skip KYC, skip `bridge/swap/stake/deposit/gas fee/mint`, deteksi scam `seed phrase/private key/drainer`
- **Dedupe + Seen 14 hari**: `config/seen_airdrops.json` TTL 14 hari, rate limit 1.5s
- **Translate**: step EN→ID (Follow, Gabung, Klaim dll)
- **Export**: `data/airdrops_OP.xlsx` + `data/airdrops_OP.csv` (CSV selalu, Excel jika pandas ada)
- **Telegram OP Digest**: top 5 by score + header 🚨 jika ada HOT, format HTML
- **Dry-run**: `--dry-run` hanya print + export, tidak kirim Telegram
- **CLI**: `--sources airdrops_io` untuk override

## Cara pakai
```bash
pip install pandas openpyxl requests  # pandas opsional (buat Excel)
# set token
echo "TELEGRAM_BOT_TOKEN=xxx" > config/.env
echo "TELEGRAM_CHAT_ID=yyy" >> config/.env

# hunter OP (kirim Telegram + export)
python scripts/hunter.py

# dry-run (cuma print + bikin Excel, tidak kirim)
python scripts/hunter.py --dry-run

# cuma 1 sumber
python scripts/hunter.py --dry-run --sources airdrops_io
```

## Cron (6 jam)
```bash
# hermes cron (jika pakai hermes)
# atau crontab -e
0 */6 * * * cd /path/airdrop-hunter && python scripts/hunter.py >> logs/hunter.log 2>&1
```

## Output
- Telegram: 5 teratas + score + heat + cara 1-3 + link
- Excel: `data/airdrops_OP.xlsx` sorted by Score DESC
- Log: `logs/hunter.log`

## Legal
Hanya scrape data publik yang 100% gratis. Tidak auto-connect wallet, tidak auto-claim. Jangan pernah kasih seed phrase.
