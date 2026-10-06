"""Unduh daftar emiten aktif dari BEI ke tickers.txt.
Kalau gagal / hasil terlalu sedikit, tickers.txt lama dibiarkan."""
import requests

URL = ("https://www.idx.co.id/primary/ListedCompany/GetCompanyProfiles"
       "?emitenType=s&start=0&length=2000")
HDR = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36",
       "Accept": "application/json", "Referer": "https://www.idx.co.id/"}

try:
    r = requests.get(URL, headers=HDR, timeout=30)
    r.raise_for_status()
    codes = sorted({d["KodeEmiten"].strip().upper() for d in r.json()["data"]
                    if len(d.get("KodeEmiten", "").strip()) == 4})
    if len(codes) > 500:
        open("tickers.txt", "w").write("\n".join(codes) + "\n")
        print("tickers.txt diperbarui:", len(codes), "saham")
    else:
        print("Hasil terlalu sedikit, tickers.txt lama dipakai:", len(codes))
except Exception as e:
    print("Gagal ambil daftar BEI, tickers.txt lama dipakai:", e)
