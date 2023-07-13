import tkinter as tk
from tkinter import ttk, messagebox
from tkinter import filedialog as fd
import pandas as pd
import threading
import os
import openai
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
import time
import csv
from pulp import *
from bardapi import Bard
from dotenv import load_dotenv


# replace these with your actual functions
def function1(url):
    load_dotenv() 


    # Set your driver executable path
    driver_path = os.getenv("driver_path")


    # Initialize webdriver
    service = Service(driver_path)
    driver = webdriver.Chrome(service=service)
    
    # Maximize the window
    driver.maximize_window()


    # Navigate to the page
    # url = 'https://www.draftkings.com/draft/contest/146153396'
    
    driver.get(url)


    # Try to find the element
    all_buttons = driver.find_elements(By.CLASS_NAME, '_1eDLeDBEB8Nc_ty5EHzmxI')[8]
    all_buttons.click()


    # Get rows and scrollable div
    rows = driver.find_elements(By.CLASS_NAME, 'ReactVirtualized__Table__row')
    scrollable_div = driver.find_element(By.CLASS_NAME, "ReactVirtualized__Grid")


    # Calculate the height of a single row
    single_row_height = driver.execute_script("return arguments[0].offsetHeight", rows[0])


    # Scroll height for 30 rows
    thirty_row_scroll_height = single_row_height * 30


    # Calculate total scroll height
    total_height = driver.execute_script("return arguments[0].scrollHeight", scrollable_div)


    # in it a set
    tx_set = set()
    er = 0
    
    # contest name
    if driver.find_elements(By.TAG_NAME, 'h3')[0].text: 
        contest = driver.find_elements(By.TAG_NAME, 'h3')[0].text
    else:
        contest = "MLB"
            
    # Scroll incrementally
    for _ in range(0, total_height, thirty_row_scroll_height):
        driver.execute_script(f"arguments[0].scrollTop = arguments[0].scrollTop + {thirty_row_scroll_height}", scrollable_div)
        # time.sleep(1)  # pause for a second


        # Append new rows
        
        temp = driver.find_elements(By.CLASS_NAME, 'ReactVirtualized__Table__row')
        for row in temp:
            try:
                html_value = row.get_attribute('innerHTML')
                if "_3t678MFxK21bzQxDUjDCCL" not in html_value and "_3r_w9gTpyFJ1fDwr2M97EY" not in html_value:        
                    tx_set.add(row.text) 
            except Exception as e:
                er += 1
                # print(er)  
    print("Er:")
    print(er)         
    
    # Initialize empty DataFrame
    df = pd.DataFrame(columns=["POS", "PLAYER", "OPP", "OPP_SP", "FPPG", "SALARY"])
    new_row = pd.DataFrame(columns=["POS", "PLAYER", "OPP", "OPP_SP", "FPPG", "SALARY"])
    # Get row text and append to DataFrame
    for row in tx_set:
        # print(row)
        if "\n" in row and row.count("\n") == 5 and "IL" not in row:
            data = row.split('\n')


            # Split fields from data
            pos = data[0]
            player = data[1]
            opp = data[2]
            opp_sp = data[3]
            fppg = data[4]
            salary = data[5]


            # Append to DataFrame
            # print(pos,player,opp,opp_sp,fppg,salary)
            new_row = pd.DataFrame({
            "POS": [pos],
            "PLAYER": [player],
            "OPP": [opp],
            "OPP_SP": [opp_sp],
            "FPPG": [fppg],
            "SALARY": [salary],
        })
        df = pd.concat([df, new_row], ignore_index=True)      
        df.drop_duplicates(inplace=True)     
    return df


def function2(url):    
    # Do your complex analysis here
    return pd.DataFrame([["SP", "J. Berrios", "TOR @ BAL", "Bradish (R)", "19.7", "$9,400"]],
                        columns=["POS", "PLAYER", "OPP", "OPP SP", "FPPG", "SALARY"])


def gpt4_api_call(contest, players):
    load_dotenv() 
    openai.api_key = os.getenv("GPT4_API_KEY")
    input_text = "how is this lineup list for the DFS in draftkings, if you have better selection consider please: \n"
    input_text += "contest: "
    input_text += contest
    input_text += "\n"
    input_text += players.to_string(index=False)
    response = openai.Completion.create(
        model="text-davinci-003",
        prompt=input_text,        
        temperature=0,
        max_tokens=512,
        top_p=1.0,
        frequency_penalty=0.0,
        presence_penalty=0.0,
        stop=["\"\"\""]
    )
    # Process the response and return the results as a DataFrame
    messagebox.showinfo("GPT4-AI Recommendation!", response.choices[0].text)


def bard_api_call(contest, players):
    load_dotenv() 
    try:
        os.environ['_BARD_API_KEY'] = os.getenv("BARD_API_KEY")
        input_text = "how is this lineup list for the DFS in draftkings, if you have better selection consider please: \n"
        input_text += "contest: "
        input_text += contest
        input_text += "\n"
        input_text += players.to_string(index=False)
        resp = Bard().get_answer(input_text)['content']
        messagebox.showinfo("Bard-AI Recommendation!", resp)
    except Exception as e:
        print("BARD exception!")


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


class DFSApp:
    def __init__(self, root, contest):
        self.root = root
        self.root.geometry('800x600')
        self.url = ""


        # Center the window
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        center_x = int(screen_width/2 - 800/2)
        center_y = int(screen_height/2 - 600/2)
        self.root.geometry(f'800x600+{center_x}+{center_y}')


        self.create_widgets()
        self.df = pd.read_csv('dfs_data.csv') if os.path.exists('dfs_data.csv') else pd.DataFrame()
        self.update_table()


    def create_widgets(self):
        title = tk.Label(self.root, text="DAILY FANTASY SPORTS", font=('Arial Black', 16))
        title.pack(pady=10)


        group = tk.LabelFrame(self.root, text="Inference Power")
        group.pack(padx=10, pady=10, fill='both', expand='yes')


        lbl = tk.Label(group, text="Please choose the power of application for checking and predictions.")
        lbl.pack(padx=10, pady=5)


        self.radio_var = tk.StringVar(value="shallow")


        radio_frame = tk.Frame(group)
        radio_frame.pack(padx=10, pady=5)


        r1 = tk.Radiobutton(radio_frame, text="Shallow Analysis", variable=self.radio_var, value="shallow")
        r1.pack(side='left')


        r2 = tk.Radiobutton(radio_frame, text="Complex Search & Analysis", variable=self.radio_var, value="complex")
        r2.pack(side='left')


        self.button = tk.Button(group, text="Scrape Data", command=self.on_button_click, font=('Helvetica', 16), width=20)
        self.button.pack(padx=10, pady=10)


        # Create URL entry field
        url_label = tk.Label(group, text="Enter URL to scrape from:")
        url_label.pack(pady=(20, 5))  # adding some vertical padding
        self.url_entry = tk.Entry(group, width=60)
        self.url_entry.pack()


        self.table = ttk.Treeview(self.root, columns=("POS", "PLAYER", "OPP", "OPP SP", "FPPG", "SALARY"), show='headings')
        # Setting the column names
        self.table.heading("POS", text="POS")
        self.table.column("POS", width=5)
        self.table.heading("PLAYER", text="PLAYER")
        self.table.column("PLAYER", width=30)
        self.table.heading("OPP", text="OPP")
        self.table.column("OPP", width=30)
        self.table.heading("OPP SP", text="OPP SP")
        self.table.column("OPP SP", width=30)
        self.table.heading("FPPG", text="FPPG")
        self.table.column("FPPG", width=5)
        self.table.heading("SALARY", text="SALARY")
        self.table.column("SALARY", width=20)
        self.table.pack(padx=10, pady=10, fill='both', expand='yes')


    def on_button_click(self):
        if self.url_entry.get() == "":
            messagebox.showinfo('Error!', 'Please fill in the contest link.')
        else:
            self.button['state'] = 'disabled'
            user_url = self.url_entry.get()
            if self.radio_var.get() == 'shallow':
                self.df = function1(user_url)
            else:
                self.df = function2(user_url)
            self.df.to_csv('dfs_data.csv', index=False)
            self.update_table()
            
            # get data
            chosen_players = solve_lineup_problem(self.df)


            # Select only required columns
            chosen_players = chosen_players[["POS", "PLAYER", "OPP", "OPP_SP", "FPPG", "SALARY"]]


            # Save to csv
            chosen_players.to_csv("chosen_players.csv", index=False)
            bard_api_call(contest, chosen_players) 
    


    def update_table(self):
        self.table.delete(*self.table.get_children())
        for row in self.df.itertuples():
            self.table.insert('', 'end', values=row[1:])
        # print(self.df)  # for debugging


    def on_data_ready(self,_):
        self.button['state'] = 'normal'
        messagebox.showinfo('DFSApp', 'Data extraction finished and ready to predict')


contest = ""
root = tk.Tk()
app = DFSApp(root, contest)
root.mainloop()