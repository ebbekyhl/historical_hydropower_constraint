def annuity(n,r):
    """Calculate the annuity factor for an asset with lifetime n years and
    discount rate of r, e.g. annuity(20,0.05)*20 = 1.6"""

    if r > 0:
        return r/(1. - 1./(1.+r)**n)
    else:
        return 1/n
    
def build_base_network(country,
                       load_csv,
                       load_scale_up,
                       CF_wind,
                       p_nom_wind,
                       p_nom_max_wind,
                       CF_solar,
                       p_nom_solar,
                       p_nom_max_solar,
                       carriers_list=['wind','solar','battery']):
    import pypsa
    import pandas as pd
    n = pypsa.Network()
    n.add("Bus","electricity bus")
    carriers = carriers_list
    n.madd("Carrier",carriers);
    hours = pd.date_range('2015-01-01T00:00Z','2015-12-31T23:00Z', freq='H')
    n.set_snapshots(hours)

    load = pd.read_csv(load_csv, sep=';', index_col=0)
    load.index = pd.to_datetime(load.index)
    n.add('Load', # pypsa component
          'el_load', # name
          bus = 'electricity bus', # bus name
          p_set = load[country]*load_scale_up
         )

    if 'wind' in carriers_list:
        n.add('Generator',
              'wind',
              bus='electricity bus',
              carrier='wind',
              p_nom = p_nom_wind,
              p_nom_extendable=True,
              p_nom_max=p_nom_max_wind, # maximum capacity can be limited due to environmental constraints
              capital_cost=1e6*annuity(30,0.07),
              marginal_cost=0.015,
              p_max_pu=CF_wind,
             )
    
    if 'solar' in carriers_list:
        n.add('Generator',
              'solar',
              bus='electricity bus',
              carrier='solar',
              p_nom = p_nom_solar,
              p_nom_extendable=True,
              p_nom_max=p_nom_max_solar, # maximum capacity can be limited due to environmental constraints
              capital_cost=1e5*annuity(30,0.07),
              marginal_cost=0.01,
              p_max_pu=CF_solar,
             )

    if 'battery' in carriers_list:
        n.add('StorageUnit',
              'battery',
              bus='electricity bus',
              carrier = 'battery',
              p_nom_extendable=True,
              capital_cost=1e6*annuity(30,0.07),
              max_hours=6,
              efficiency_store=0.95,
              efficiency_dispatch=0.95,
              cyclic_state_of_charge=True
             )
    
    return n

#def solve(n):
#    n.lopf(n.snapshots, 
#            pyomo=False,
#            solver_name='gurobi')

def add_wind_constraint(n):
    """
    This function adds a constraint which is used as an example
    """
    lhs = n.model.variables["Generator-p"].sel(Generator='wind').sum()
    n.model.add_constraints(lhs <= 1e6, name="wind total constraint")

def add_capacity_addition_constraint(n):
    """
    This function adds a constraint which is used as an example
    """
    lhs = n.model.variables["Generator-p_nom"].sel({"Generator-ext":'wind'}) - n.generators.p_nom['wind'].sum()
    n.model.add_constraints(lhs <= 1000, name="wind total constraint")
    
def add_hydropower_constraint(n):
    """
    This function adds a constraint on the hydropower dispatch ...
    """
    
    kwargs = {'snapshot':30*24} # monthly (approx.) rolling sum
    n.model.variables["StorageUnit-p_dispatch"].sel(StorageUnit='hydro').rolling_sum(**kwargs)
    
    # historical_bound = 
    
    rhs = historical_dispatch_bound
    lhs = n.model.variables["StorageUnit"].sel(StorageUnit='hydro').sum()
    n.model.add_constraints(lhs <= rhs, name="hydro dispatch constraint")
    
    #model_monthly_dispatch = n.storage_units_t.p['hydro'].resample('m').sum()/1e3
    #historical_monthly_dispatch_min = df.resample('m').sum().min(axis=1)
    #historical_monthly_dispatch_max = df.resample('m').sum().max(axis=1)
    
    #lhs = historical_monthly_dispatch_min - model_monthly_dispatch

    #n.model.add_constraints(lhs <= 0, name="hydropower_constraint")

def extra_functionality(n, snapshots):
    """
    Collects supplementary constraints which will be passed to
    ``pypsa.optimization.optimize``.
    If you want to enforce additional custom constraints, this is a good
    location to add them.
    """
    #add_hydropower_constraint(n) # does not work yet ... 
    add_wind_constraint(n) # works very well
    #add_capacity_addition_constraint(n)

def solve_network(n,
                  **kwargs):
    
    import logging
    import pypsa

    logger = logging.getLogger(__name__)
    pypsa.pf.logger.setLevel(logging.WARNING)

    
    solver_options = {'threads': 4,
                      'method': 2, # barrier
                      'crossover': 0,
                      'BarConvTol': 1.e-6,
                      'Seed': 123,
                      'AggFill': 0,
                      'PreDual': 0,
                      'GURO_PAR_BARDENSETHRESH': 200,
                      'seed': 10}
    
    cf_solving = {'formulation': 'kirchhoff',
                  'clip_p_max_pu': 1.e-2,
                  'load_shedding': False,
                  'noisy_costs': True,
                  'skip_iterations': True,
                  'track_iterations': False,
                  'min_iterations': 4,
                  'max_iterations': 6,
                  'seed': 123}
    
    solver_name = 'gurobi'
                  
    track_iterations = cf_solving.get("track_iterations", False)
    min_iterations = cf_solving.get("min_iterations", 4)
    max_iterations = cf_solving.get("max_iterations", 6)

    skip_iterations = cf_solving.get("skip_iterations", False)
    if not n.lines.s_nom_extendable.any():
        skip_iterations = True
        logger.info("No expandable lines found. Skipping iterative solving.")

    if skip_iterations:
        status, condition = n.optimize(solver_name=solver_name,
                                       extra_functionality=extra_functionality,
                                       **solver_options,
                                       **kwargs,
        )
    else:
        status, condition = n.optimize.optimize_transmission_expansion_iteratively(
            solver_name=solver_name,
            track_iterations=track_iterations,
            min_iterations=min_iterations,
            max_iterations=max_iterations,
            extra_functionality=extra_functionality,
            **solver_options,
            **kwargs,
        )

    if status != "ok":
        logger.warning(
            f"Solving status '{status}' with termination condition '{condition}'"
        )
    if "infeasible" in condition:
        raise RuntimeError("Solving status 'infeasible'")

    return n

    
    