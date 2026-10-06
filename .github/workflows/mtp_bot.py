"""
MTP Daily Signal Bot (versi gratis: yfinance + Telegram)
Install : pip install yfinance pandas requests
Jalankan: python mtp_bot.py          (kirim ke Telegram)
          python mtp_bot.py --dry    (cetak saja, tanpa kirim)
File opsional di folder yang sama:
  tickers.txt  -> 1 kode saham per baris (tanpa .JK). Isi sebanyak mungkin saham IDX.
  syariah.txt  -> daftar kode saham syariah (ISSI/DES)
  uma.txt      -> kode saham yang sedang kena UMA (isi manual dari pengumuman BEI)
"""
import os, sys, datetime as dt
import pandas as pd, yfinance as yf, requests

# ============ CONFIG ============
TOKEN   = os.getenv("TG_TOKEN", "ISI_TOKEN_BOT")
CHAT_ID = os.getenv("TG_CHAT_ID", "ISI_CHAT_ID")

CH_MIN      = 10.0     # CH10: high hari ini >= +10% dari close kemarin
MIN_PRICE   = 50
MIN_VALUE   = 5e9      # nilai transaksi minimal (Rp)
MIN_VR      = 2.0      # volume hari ini / rata-rata volume VR_WIN hari
VR_WIN      = 20
LOOKBACK    = "2y"
TARGETS     = [1, 2, 3, 5]   # % target profit yang diuji
HOLDS       = [1, 3, 5]      # max hold (hari) yang diuji
MIN_TRADES  = 20
# ================================

def read_list(fn):
    return set(x.strip().upper() for x in open(fn)) if os.path.exists(fn) else set()

def load_data(tickers):
    raw = yf.download([t + ".JK" for t in tickers], period=LOOKBACK,
                      group_by="ticker", auto_adjust=False, progress=False, threads=True)
    out = {}
    for t in tickers:
        try:
            df = raw[t + ".JK"].dropna()
            if len(df) > 60: out[t] = df
        except Exception:
            pass
    return out

def add_features(df):
    d = df.copy()
    pc = d["Close"].shift(1)
    d["CH"] = (d["High"] / pc - 1) * 100
    d["CC"] = (d["Close"] / pc - 1) * 100
    d["GAP"] = d["CH"] - d["CC"]
    d["MA13"] = d["Close"].rolling(13).mean()
    d["MA21"] = d["Close"].rolling(21).mean()
    d["VALUE"] = d["Close"] * d["Volume"]
    d["VR"] = d["Volume"] / d["Volume"].rolling(VR_WIN).mean().shift(1)
    return d

def backtest(d):
    """Setiap hari CH>=CH_MIN dianggap sinyal; beli open besok, jual saat target
    tercapai (pakai High) atau di close hari terakhir hold. Pilih kombinasi terbaik."""
    sig = d.index[d["CH"] >= CH_MIN][:-1]
    idx = {k: i for i, k in enumerate(d.index)}
    best = None
    for tp in TARGETS:
        for hold in HOLDS:
            rets = []
            for s in sig:
                i = idx[s] + 1
                if i + hold > len(d): continue
                entry = d["Open"].iloc[i]
                if entry <= 0: continue
                r = None
                for j in range(i, i + hold):
                    if d["High"].iloc[j] >= entry * (1 + tp / 100):
                        r = tp; break
                if r is None:
                    r = (d["Close"].iloc[i + hold - 1] / entry - 1) * 100
                rets.append(r)
            if len(rets) < MIN_TRADES: continue
            s_ = pd.Series(rets)
            win, loss = s_[s_ > 0].sum(), -s_[s_ < 0].sum()
            pf = win / loss if loss > 0 else float("inf")
            wr = (s_ > 0).mean() * 100
            cand = dict(tp=tp, hold=hold, wr=wr, pf=pf, n=len(rets))
            if best is None or (cand["pf"], cand["wr"]) > (best["pf"], best["wr"]):
                best = cand
    return best

def nch_sr(d):
    """NCH = jumlah hari CH10 dalam data; SR = % hari CH10 yang close-nya
    masih di atas close kemarin (CC>0). (Tebakan, ubah sesuai definisi Anda)"""
    ev = d[d["CH"] >= CH_MIN]
    return len(ev), (ev["CC"] > 0).mean() * 100 if len(ev) else 0

def f(x, n=2): return f"{x:,.{n}f}".replace(",", "X").replace(".", ",").replace("X", ".")
def i(x): return f"{x:,.0f}".replace(",", ".")

def info(t):
    try:
        inf = yf.Ticker(t + ".JK").info
        ff = (inf.get("floatShares") or 0) / (inf.get("sharesOutstanding") or 1) * 100
        dy = (inf.get("dividendYield") or 0) * 100
        return ff, dy, inf.get("netIncomeToCommon") or 0
    except Exception:
        return 0, 0, 0

def build():
    tickers = sorted(read_list("tickers.txt")) or ["KDTN", "MITI", "BBCA", "BBRI", "GOTO"]
    syariah, uma = read_list("syariah.txt"), read_list("uma.txt")
    data = load_data(tickers)
    rows = []
    for t, df in data.items():
        d = add_features(df)
        last = d.iloc[-1]
        if not (last["CH"] >= CH_MIN and last["Close"] >= MIN_PRICE
                and last["VALUE"] >= MIN_VALUE and last["VR"] >= MIN_VR):
            continue
        rows.append((t, d, last))
    rows.sort(key=lambda r: -r[2]["VALUE"])

    today = dt.date.today().strftime("%d-%m-%Y")
    L = [f"Snapshot: {today}", f"Total kandidat: {len(rows)} saham", "",
         "=" * 24, "A. ONE DAY TRADING", "=" * 24, ""]
    for n, (t, d, x) in enumerate(rows, 1):
        ff, dy, ni = info(t)
        nch, sr = nch_sr(d)
        bt = backtest(d)
        L += [f"{n}. {t} - CH10", f"Last: {i(x.Close)}",
              f"MA13: {i(x.MA13)} | MA21: {i(x.MA21)}",
              f"Value: {i(x.VALUE)}", f"VR: {f(x.VR)}x",
              f"Syariah: {'Ya' if t in syariah else 'Tidak'}",
              f"Free Float: {f(ff)}%",
              f"Deviden: {f(dy)}% | Net Income: {i(ni)}",
              f"{'⚠️ UMA: YA' if t in uma else '✅ UMA: TIDAK'}",
              f"Ket: CH {f(x.CH)}% | CC {f(x.CC)}% | Gap {f(x.GAP)}% | NCH {nch} | SR {sr:.0f}%", ""]
        if bt:
            L += ["🤖 Rekomendasi AI:",
                  f"Target Profit: {bt['tp']}% | Max Hold: {bt['hold']}D",
                  f"Backtest: WR {f(bt['wr'])}% | PF {f(bt['pf'],3)} | Trades {bt['n']}", ""]
        else:
            L += ["🤖 Rekomendasi AI: data backtest kurang", ""]
    return "\n".join(L)

def send(text):
    for k in range(0, len(text), 4000):  # batas Telegram 4096 karakter
        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                      data={"chat_id": CHAT_ID, "text": text[k:k + 4000]})

if __name__ == "__main__":
    msg = build()
    print(msg) if "--dry" in sys.argv else send(msg)
