from c import *
from u import *
import time
import datetime
import threading
import ccxt

class BotBinanceFutures():

    def __init__(self):

        self.bool_start = False
        self.bool_send_message = False

        self.bnc = ccxt.binance(config={'apiKey': BN_ACCESS_KEY, 'secret': BN_SECRET_KEY, 'enableRateLimit': True, 'options': {'defaultType': 'future'}})

    def get_unrealized_df(self, df):
        if not df is None:
            direct = df['open'] < df['close']
            df['direct_prev_0'] = direct
            df['direct_prev_1'] = direct.shift(1)
            df['direct_prev_2'] = direct.shift(2)
            return df

    def is_in_range(self, t, s, e):
        return s <= t <= e

    def analyze_unrealized(self, tk):

        send_text = ''
        send_text = send_text + f'{tk}'

        df_30 = get_bnc_df(self.bnc, tk, '30m', 120)

        if not df_30 is None:
            df_30['macd'], _, _ = indicator_macd(df_30['close'], 12, 26, 9)
            df_30_t = df_30.tail(3).head(2)
            macd_1 = df_30_t['macd'].iloc[-2]
            macd_0 = df_30_t['macd'].iloc[-1]
            macd_d = 'Rise' if macd_1 < macd_0 else 'Fall'
            send_text = send_text + f'\nM : {round(macd_1, 8)} → {round(macd_0, 8)} {macd_d}'

        df = self.get_unrealized_df(get_bnc_df(self.bnc, tk, '15m', 4*24*7))
        ul = []

        if not df is None:

            df.drop(df.tail(1).index,inplace=True)

            # df_start = df.head(1).index[0]
            # df_end = df.tail(1).index[0]
            close_last = float(df.tail(1)['close'].iloc[-1])

            # send_text = send_text + f'\nP : {df_start} ~ {df_end}'

            df_len = len(df)
            cnt = 1
            for i, r in df.iterrows():

                _time = i.strftime('%Y-%m-%d %H:%M:%S')
                close = float(r['close'])
                digit = 0
                if tk == 'XRP/USDT':
                    digit = 4
                elif tk == 'MATIC/USDT' or tk == 'LINA/USDT':
                    digit = 5
                tp_p = close + (close * 0.0006)
                tp_p = round(tp_p, digit)
                tp_m = close - (close * 0.0006)
                tp_m = round(tp_m, digit)
                high = float(r['high'])
                low = float(r['low'])
                direct_prev_0 = r['direct_prev_0']
                direct_prev_1 = r['direct_prev_1']
                direct_prev_2 = r['direct_prev_2']

                is_last = cnt == df_len

                if len(ul) > 0:
                    for l in ul:
                        if (l['e'] == '') & (self.is_in_range(float(l['tp']), low, high)):
                            l['e'] = _time

                if direct_prev_0 == direct_prev_1:
                    if direct_prev_0:
                        ul.append({'s': _time, 'e': '', 'c': '2', 'ot': 'l', 'op': close, 'tp': tp_p})
                        if (macd_0 > 0) & is_last:
                            send_text = send_text + f'\nN : 2-L - TP {round(tp_p, 8)}'
                    else:
                        ul.append({'s': _time, 'e': '', 'c': '2', 'ot': 's', 'op': close, 'tp': tp_m})
                        if (macd_0 < 0) & is_last:
                            send_text = send_text + f'\nN : 2-S - TP {round(tp_m, 8)}'
                
                if direct_prev_0 == direct_prev_1 == direct_prev_2:
                    if direct_prev_0:
                        ul.append({'s': _time, 'e': '', 'c': '3', 'ot': 's', 'op': close, 'tp': tp_m})
                        if (macd_0 < 0) & is_last:
                            send_text = send_text + f'\nN : 3-S - TP {round(tp_m, 8)}'
                    else:
                        ul.append({'s': _time, 'e': '', 'c': '3', 'ot': 'l', 'op': close, 'tp': tp_p})
                        if (macd_0 > 0) & is_last:
                            send_text = send_text + f'\nN : 3-L - TP {round(tp_p, 8)}'
                
                cnt = cnt + 1

            _ul_l = [_l for _l in ul if ((_l['e'] == '') & (_l['ot'] == 'l'))]
            _ul_s = [_l for _l in ul if ((_l['e'] == '') & (_l['ot'] == 's'))]

            send_text = send_text + f'\nS : S {len(_ul_s)} / L {len(_ul_l)}'

            near_price_up = []
            near_price_dn = []

            if len(_ul_l) > 0:

                for _ull in _ul_l:

                    tp = _ull['tp']
                    # send_text = send_text + f'\n* {c}-{ot} : TP {round(tp, 8)}'

                    if close_last > tp:
                        near_price_dn.append(tp)
                    elif close_last < tp:
                        near_price_up.append(tp)

            if len(_ul_s) > 0:

                for _uls in _ul_s:

                    tp = _uls['tp']
                    # send_text = send_text + f'\n* {c}-{ot} : TP {round(tp, 8)}'

                    if close_last > tp:
                        near_price_dn.append(tp)
                    elif close_last < tp:
                        near_price_up.append(tp)

            send_text = send_text + f'\nO :'
            if len(near_price_dn) > 0:
                tp_max = max(near_price_dn)
                send_text = send_text + f' {round(tp_max, 8)} <'
            # send_text = send_text + f' Close {round(close_last, 8)}'
            send_text = send_text + f' C'
            if len(near_price_up) > 0:
                tp_min = min(near_price_up)
                send_text = send_text + f' < {round(tp_min, 8)}'

            return send_text
        
    def send_message(self):

        if self.bool_send_message == False:

            tn = datetime.datetime.now()
            tn_0 = tn.replace(hour=0, minute=0, second=0)
            tn_d = int(((tn - tn_0).seconds) % 900)
            time.sleep(900 - tn_d)
            self.bool_send_message = True

        _tn = datetime.datetime.now()

        tks = ['BTC/USDT', 'ETH/USDT', 'XRP/USDT']
        send_text = ''
        for tk in tks:
            send_text = send_text + f'\n\n' + self.analyze_unrealized(tk)

        __tn = datetime.datetime.now()
        __tn_min = __tn.minute % 15
        __tn_sec = __tn.second

        self.time_backtest = threading.Timer(900 - (60 * __tn_min) - __tn_sec, self.send_message)
        self.time_backtest.start()

        line_message(f'BotBinanceFutures {send_text}')

        

if __name__ == '__main__':

    bbf = BotBinanceFutures()
    # bbf.send_message()

    while True:

        try:

            tn = datetime.datetime.now()
            tn_start = tn.replace(hour=0, minute=0, second=0)

            if tn >= tn_start and bbf.bool_start == False:
                bbf.send_message()
                bbf.bool_start = True

        except Exception as e:

            line_message(f"BotBinanceFutures Error : {e}")
            break