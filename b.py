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

        df = self.get_unrealized_df(get_bnc_df(self.bnc, tk, '15m', 4*24*14))
        ul = []

        if not df is None:

            df.drop(df.tail(1).index,inplace=True)
            close_last = float(df.tail(1)['close'].iloc[-1])
            
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

                if len(ul) > 0:
                    for l in ul:
                        if (l['e'] == '') & (self.is_in_range(float(l['tp']), low, high)):
                            l['e'] = _time

                if direct_prev_0 == direct_prev_1:
                    if direct_prev_0:
                        ul.append({'s': _time, 'e': '', 'c': '2', 'ot': 'l', 'op': close, 'tp': tp_p})
                    else:
                        ul.append({'s': _time, 'e': '', 'c': '2', 'ot': 's', 'op': close, 'tp': tp_m})
                
                if direct_prev_0 == direct_prev_1 == direct_prev_2:
                    if direct_prev_0:
                        ul.append({'s': _time, 'e': '', 'c': '3', 'ot': 's', 'op': close, 'tp': tp_m})
                    else:
                        ul.append({'s': _time, 'e': '', 'c': '3', 'ot': 'l', 'op': close, 'tp': tp_p})
                
            _ul_l = [_l for _l in ul if ((_l['e'] == '') & (_l['ot'] == 'l'))]
            _ul_s = [_l for _l in ul if ((_l['e'] == '') & (_l['ot'] == 's'))]
            _ul_l_len = len(_ul_l)
            _ul_s_len = len(_ul_s)

            send_text = send_text + f'{tk} : S {_ul_s_len} / L {_ul_l_len}'

            near_price_up = []
            near_price_dn = []

            if len(_ul_l) > 0:
                for _ull in _ul_l:
                    tp = _ull['tp']
                    if close_last > tp:
                        near_price_dn.append(tp)
                    elif close_last < tp:
                        near_price_up.append(tp)

            if len(_ul_s) > 0:

                for _uls in _ul_s:
                    tp = _uls['tp']
                    if close_last > tp:
                        near_price_dn.append(tp)
                    elif close_last < tp:
                        near_price_up.append(tp)

            if len(near_price_dn) > 0:
                near_price_dn = sorted(near_price_dn)
                npd_cnt = 1
                for npd in near_price_dn:
                    if npd_cnt == 1:
                        send_text = send_text + f'\n{npd}'
                    else:
                        send_text = send_text + f', {npd}'
                    npd_cnt += 1
            send_text = send_text + f'\nCurrent Price : {close_last}'
            if len(near_price_up) > 0:
                near_price_up = sorted(near_price_up)
                npu_cnt = 1
                for npu in near_price_up:
                    if npu_cnt == 1:
                        send_text = send_text + f'\n{npu}'
                    else:
                        send_text = send_text + f', {npu}'
                    npu_cnt += 1

            return send_text
        
    def send_message(self):

        if self.bool_send_message == False:

            tn = datetime.datetime.now()
            tn_0 = tn.replace(hour=0, minute=0, second=0)
            tn_d = int(((tn - tn_0).seconds) % 900)
            time.sleep(900 - tn_d)
            self.bool_send_message = True

        _tn = datetime.datetime.now()

        tks = ['BTC/USDT', 'BCH/USDT', 'XRP/USDT']
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