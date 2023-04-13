def plot_layout(fs):
    import matplotlib.pyplot as plt
    plt.style.use('seaborn-ticks')
    plt.rcParams['axes.labelsize'] = fs
    plt.rcParams['xtick.labelsize'] = fs
    plt.rcParams['ytick.labelsize'] = fs
    plt.rcParams['xtick.direction'] = 'out'
    plt.rcParams['ytick.direction'] = 'out'
    plt.rcParams['axes.axisbelow'] = True
    plt.rcParams['legend.title_fontsize'] = fs
    plt.rcParams['legend.fontsize'] = fs

def plot_historical_dispatch(country,
                             long_country_name,
                             freq='h'):
    import pandas as pd
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    
    timescales = {'h':'hourly',
                  'd':'daily',
                  'w':'weekly',
                  'm':'monthly'}
    
    historical_dispatch = pd.read_csv(
        'ENTSOE_data/dispatch_' + long_country_name[country] + '_2015-2018.csv',index_col=0)
    historical_dispatch.index = pd.to_datetime(historical_dispatch.index)
    df = pd.DataFrame(index=pd.date_range('1/1/2015','1/1/2016',freq='h',closed='left'))
    df1 = pd.DataFrame(historical_dispatch)
    df1['year'] = df1.index.year
    for year in df1.index.year.unique():
        df1_year = df1.query('year == @year')
        df1_year = df1_year[~df1_year.index.duplicated(keep='first')]

        if (year % 4 == 0) and (year % 100 != 0): # leap year    
            day_29 = df1_year.index.day == 29
            feb_29 = df1_year[day_29][df1_year[day_29].index.month == 2]
            df1_year = df1_year.drop(index=feb_29.index)

        df[year] = df1_year.disp.values

    df_min = df.min(axis=1).resample(freq).sum()
    df_max = df.max(axis=1).resample(freq).sum()

    fig, ax = plt.subplots()
    x = df_min.index
    y1 = df_min
    y2 = df_max
    ax.fill_between(x,y1,y2,alpha=0.5,label='Historical (2015-2018)')

    ax.set_xlim(min(x),max(x))
    ax.legend()
    ax.set_ylabel(timescales[freq] + ' hydro dispatch [GWh]')

    fmt = mdates.DateFormatter('%b')
    ax.xaxis.set_major_formatter(fmt);

def plot_hydro_operation(n,
                         df_historical,
                         hydro_inflow,
                         freq='w'):
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    import pandas as pd # hello

    timescales = {'h':'hourly',
                  'd':'daily',
                  'w':'weekly',
                  'm':'monthly'}
    
    markers = {'h':'.',
              'd':'.',
              'w':'.',
              'm':'x'}
    
    hydro_dispatch = n.storage_units_t.p['hydro']

    fig,ax = plt.subplots(figsize=(10,5))
    
    if freq == 'm':
        delta = 4
    else:
        delta = 0
    
    x_d = hydro_dispatch.resample(freq).sum().index - pd.Timedelta(weeks=delta)
    x_i = hydro_inflow.resample(freq).sum().index - pd.Timedelta(weeks=delta)
    ax.plot(x_d, hydro_dispatch.resample(freq).sum()/1e6,ls='-',marker=markers[freq],lw=1,label='Modeled dispatch',color='#003D73')
    ax.plot(x_i, hydro_inflow.resample(freq).sum()/1e6,ls='-',marker=markers[freq],lw=1,label='Inflow',color='#EE7F00')
    ax.set_ylabel('Norwegian reservoir \n ' + timescales[freq] + ' aggregate [TWh]')
    ax.set_xlim(min(x_i)-pd.Timedelta(days=5),max(x_i)+pd.Timedelta(days=5));
    
    df_min = df_historical.min(axis=1)
    df_max = df_historical.max(axis=1)
    
    x = df_min.resample(freq).sum().index - pd.Timedelta(weeks=delta)
        
    y1 = df_min.resample(freq).sum()/1e3 # convert GWh to TWh
    y2 = df_max.resample(freq).sum()/1e3 # convert GWh to TWh
    ax.fill_between(x,y1,y2,alpha=0.5,label='Historical dispatch')

    fmt = mdates.DateFormatter('%b')
    ax.grid()
    ax.xaxis.set_major_formatter(fmt)
    ax.legend(frameon=True);

def plot_electricity_supply(n,
                       tech_colors,
                       freq='w'):
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    import pandas as pd

    timescales = {'h':'hourly',
                  'd':'daily',
                  'w':'weekly',
                  'm':'monthly'}
    
    fig,ax = plt.subplots(figsize=(10,5))
    carriers_list = list(n.carriers.index).copy()
    #carriers_list.remove('hydro')
    df = pd.DataFrame(index=n.snapshots)
    for carrier in carriers_list:
        if carrier != 'battery' and carrier != 'hydro':
            df[carrier] = n.generators_t.p[carrier]/1e3
        else:
            storage_t = n.storage_units_t.p[carrier]/1e3
            storage_t[storage_t<0] = 0
            df[carrier] = storage_t
            
    #print(df.max())
    df.resample(freq).sum().plot.area(ax=ax,
                                     stacked=True,
                                     color=[tech_colors[i] for i in df.columns],lw=0)
            
    ax.set_ylabel(timescales[freq] + ' energy supply [GWh]')
    ax.set_xlim(min(n.snapshots),max(n.snapshots));
    ax.grid()
    
    fmt = mdates.DateFormatter('%b')
    ax.xaxis.set_major_formatter(fmt)
    ax.legend(frameon=True);

def plot_total_electricity_supply(n,tech_colors):
    import matplotlib.pyplot as plt
    import pandas as pd

    supply = pd.DataFrame(n.generators_t.p.sum(),columns=['MWh']).T
    supply['hydro'] = n.storage_units_t.p['hydro'].sum()
    supply /= 1e6 # convert MWh to TWh 
    fig,ax = plt.subplots(figsize=(10,5))
    supply.plot.bar(ax=ax,
                    stacked=True,
                    color=[tech_colors[i] for i in supply.columns])
    
    ax.set_xticklabels([])
    ax.set_ylabel('TWh')
