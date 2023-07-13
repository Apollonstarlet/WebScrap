import pandas as pd
import os
from pulp import *

def solve_lineup_problem(df):
    # Split POS into list of positions
    df['POS'] = df['POS'].apply(lambda x: x.split('/'))

    # Replace '-' with 0 in FPPG
    df['FPPG'] = df['FPPG'].replace('-', 0).astype(float)

    # Remove $ and , from SALARY and convert to int
    df['SALARY'] = df['SALARY'].apply(lambda x: int(x.replace('$', '').replace(',', '')) if isinstance(x, str) else x)

    # Flatten DataFrame so each row corresponds to one player-position
    df = df.explode('POS')
    df.reset_index(drop=True, inplace=True)

    # Define the problem
    prob = LpProblem("DFS", LpMaximize)

    # Decision variables
    player_vars = LpVariable.dicts("Chosen", df.index, cat='Binary')

    # Objective function
    prob += lpSum(player_vars[i] * df.loc[i, 'FPPG'] for i in df.index)

    # Constraints
    prob += lpSum(player_vars[i] * df.loc[i, 'SALARY'] for i in df.index) <= 50000 # Total salary
    prob += lpSum(player_vars[i] * df.loc[i, 'SALARY'] for i in df.index) >= 45000 # Minimum salary

    # Exact number of players for each position
    prob += lpSum(player_vars[i] for i in df.index[df['POS'].isin(['SP', 'RP'])]) == 2 # 2 Pitchers
    for pos in ['C', '1B', '2B', '3B', 'SS', 'OF']:
        prob += lpSum(player_vars[i] for i in df.index[df['POS'] == pos]) == (1 if pos != 'OF' else 3)  # 1 player for each position except OF where we need 3

    # Solve the problem
    prob.solve()

    # Get the chosen players
    chosen_players = df[df.index.isin([i for i in df.index if player_vars[i].varValue == 1])].copy()  # add .copy()

    # Reorder chosen_players dataframe
    position_order = ['SP', 'RP', 'C', '1B', '2B', '3B', 'SS', 'OF']
    chosen_players['POS'] = pd.Categorical(chosen_players['POS'], categories=position_order, ordered=True)
    chosen_players.sort_values('POS', inplace=True)

    return chosen_players

# read data
df = pd.read_csv('dfs_data.csv') if os.path.exists('dfs_data.csv') else pd.DataFrame()

chosen_players = solve_lineup_problem(df)

# Select only required columns
chosen_players = chosen_players[["POS", "PLAYER", "OPP", "OPP_SP", "FPPG", "SALARY"]]

# Save to csv
chosen_players.to_csv("chosen_players.csv", index=False)
