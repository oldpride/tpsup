dates:2018.01.01+10000000?31
times:10000000?24:00:00.0000
qtys:100*1+10000000?100
ixs:10000000?3
syms:`aapl`amzn`googl ixs
pxs:(1+10000000?0.03)*172.0 1189.0 1073.0 ixs
t:([] date:dates;time:times;sym:syms;qty:qtys;px:pxs)
t:`date`time xasc t

show 5#select vwap:qty wavg px by date,time.hh,time.mm from t where sym=`aapl, date=2018.01.01, time.hh=01

exit 0
