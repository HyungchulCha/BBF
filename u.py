from c import *
from pprint import pprint
import pandas as pd
import numpy as np
import pickle
import requests
import os
import ccxt


# Binance

def get_bnc_df(bnc, tk, tf, lm):
    ohlcv = bnc.fetch_ohlcv(tk, timeframe=tf, limit=lm)
    if not (ohlcv is None) and len(ohlcv) >= lm:
        df = pd.DataFrame(ohlcv, columns=['datetime', 'open', 'high', 'low', 'close', 'volume'])
        pd_ts = pd.to_datetime(df['datetime'], utc=True, unit='ms')
        pd_ts = pd_ts.dt.tz_convert("Asia/Seoul")
        pd_ts = pd_ts.dt.tz_localize(None)
        df.set_index(pd_ts, inplace=True)
        df = df[['open', 'high', 'low', 'close', 'volume']]
        return df

def get_available_order_ticker(bnc):
    mks = bnc.load_markets()
    tks = []
    
    for mk in mks:
        
        if \
        mk.endswith('/USDT:USDT') and \
        mks[mk]['active'] == True and \
        mks[mk]['info']['status'] == 'TRADING' \
        :
            mk = mk.replace(':USDT', '')
            # df = get_bnc_df(bnc, mk, '1d', 2).head(1)
            # vl = float(df['volume'].iloc[-1])
            tks.append(mk)
            # tks.append({'t': mk, 'v': vl})

    # tks_srt = sorted(tks, key=lambda t: float(t['v']))[-10:]
    # tks = [_t['t'] for _t in tks_srt]
    
    return tks


# Strategy

def Strategy(df):
    df = indicator_supertrend(df)
    if not df is None:
        df['low_prev'] = df['low'].shift()
        df['rsi'] = indicator_rsi(df['close'], 14)
        df['rsi_prev'] = df['rsi'].shift()
        return df


# Indicator

def indicator_supertrend(df, atr_period=10, multiplier=3.0):

    if not df is None:

        high = df['high']
        low = df['low']
        close = df['close']
        
        price_diffs = [high - low, high - close.shift(), close.shift() - low]
        true_range = pd.concat(price_diffs, axis=1)
        true_range = true_range.abs().max(axis=1)
        atr = true_range.ewm(alpha=1/atr_period,min_periods=atr_period).mean() 
        
        hl2 = (high + low) / 2
        final_upperband = upperband = hl2 + (multiplier * atr)
        final_lowerband = lowerband = hl2 - (multiplier * atr)
        
        supertrend = [True] * len(df)
        
        for i in range(1, len(df.index)):
            curr, prev = i, i-1
            
            if close[curr] > final_upperband[prev]:
                supertrend[curr] = True
            elif close[curr] < final_lowerband[prev]:
                supertrend[curr] = False
            else:
                supertrend[curr] = supertrend[prev]
                
                if supertrend[curr] == True and final_lowerband[curr] < final_lowerband[prev]:
                    final_lowerband[curr] = final_lowerband[prev]
                if supertrend[curr] == False and final_upperband[curr] > final_upperband[prev]:
                    final_upperband[curr] = final_upperband[prev]

            if supertrend[curr] == True:
                final_upperband[curr] = np.nan
            else:
                final_lowerband[curr] = np.nan

        df['supertrend'] = supertrend
        df['supertrend_prev'] = df['supertrend'].shift()
        
        return df


def indicator_bollinger_band_width(data, n=20, k=2):
    data['MA'] = data['close'].rolling(window=n).mean()
    data['Std'] = data['close'].rolling(window=n).std()
    data['UpperBand'] = data['MA'] + (k * data['Std'])
    data['LowerBand'] = data['MA'] - (k * data['Std'])
    data['BBW'] = (data['UpperBand'] - data['LowerBand']) / data['MA']
    return data


def indicator_fibonacci(pb, ph):
    
    pzr = (ph - pb * 1.618) / (1 - 1.618)
    p02 = pzr - ((pzr - pb) * 0.236)
    p03 = pzr - ((pzr - pb) * 0.382)
    p05 = pzr - ((pzr - pb) * 0.5)
    p06 = pzr - ((pzr - pb) * 0.618)
    p07 = pzr - ((pzr - pb) * 0.786)
    px1 = pzr - ((pzr - pb) * 1.618)
    px2 = pzr - ((pzr - pb) * 2.618)
    px3 = pzr - ((pzr - pb) * 3.618)
    px4 = pzr - ((pzr - pb) * 4.618)

    return pzr, p02, p03, p05, p06, p07, px1, px2, px3, px4


def indicator_volume_oscillator(data, short_window, long_window):
    short_ma = data.ewm(span=short_window, min_periods=short_window).mean()
    long_ma = data.ewm(span=long_window, min_periods=long_window).mean()
    volume_oscillator = ((short_ma - long_ma) / long_ma) * 100
    return volume_oscillator


def indicator_ema(data, window):
    ema = data.ewm(span=window, adjust=False).mean()
    return ema


def indicator_macd(data, short_window, long_window, signal_window):
    short_ema = data.ewm(span=short_window, adjust=False).mean()
    long_ema = data.ewm(span=long_window, adjust=False).mean()
    macd_line = short_ema - long_ema
    signal_line = macd_line.ewm(span=signal_window, adjust=False).mean()
    macd_histogram = macd_line - signal_line
    return macd_line, signal_line, macd_histogram


def indicator_rsi(data, window):
    diff = data.diff(1)
    up = diff.where(diff > 0, 0)
    down = -diff.where(diff < 0, 0)
    avg_gain = up.rolling(window=window).mean()
    avg_loss = down.rolling(window=window).mean()
    avg_gain = up.ewm(alpha=(1/window), min_periods=window).mean()
    avg_loss = down.ewm(alpha=(1/window), min_periods=window).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def indicator_ma(data, window):
    return data.rolling(window=window).mean()


# Line

def line_message(msg):
    print(msg)
    requests.post(LINE_URL, headers={'Authorization': 'Bearer ' + LINE_TOKEN}, data={'message': msg})
    requests.post(LINE_URL, headers={'Authorization': 'Bearer ' + LINE_TOKEN_IN}, data={'message': msg})



# Etc

def save_xlsx(url, df):
    df.to_excel(url)


def load_xlsx(url):
    return pd.read_excel(url)


def save_file(url, obj):
    with open(url, 'wb') as f:
        pickle.dump(obj, f)


def load_file(url):
    with open(url, 'rb') as f:
        return pickle.load(f)
    

def delete_file(url):
    if os.path.exists(url):
        for file in os.scandir(url):
            os.remove(file.path)


def get_qty(crnt_p, max_p):
    q = int(max_p / crnt_p)
    return 1 if q == 0 else q


def get_ror(pv, nv, pr=1, pf=0.001, spf=0):
    cr = ((nv - (nv * pf) - (nv * spf)) / (pv + (pv * pf)))
    return cr * pr