import tkinter as tk
from tkinter import ttk
from tkinter import filedialog, messagebox
import requests
from datetime import datetime, timedelta
import csv
import json
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class ValueBetFinder:
    def __init__(self, root):
        self.root = root
        self.root.title("Value Bet Finder")
        self.root.geometry("800x600")
        self.root.configure(bg='#f0f0f0')
        
        # Market mappings for predictions
        self.PREDICTION_TYPES = {
            'fulltime-result-probability': {
                'home': 'Home',
                'away': 'Away',
                'draw': 'Draw'
            },
            'over-under-1_5-probability': {
                'yes': 'Over 1.5',
                'no': 'Under 1.5'
            },
            'over-under-2_5-probability': {
                'yes': 'Over 2.5',
                'no': 'Under 2.5'
            },
            'over-under-3_5-probability': {
                'yes': 'Over 3.5',
                'no': 'Under 3.5'
            },
            'both-teams-to-score-probability': {
                'yes': 'BTTS Yes',
                'no': 'BTTS No'
            }
        }
        
        # Style configuration
        self.style = ttk.Style()
        self.style.configure('Header.TLabel', font=('Arial', 9, 'bold'))
        self.style.configure('Custom.TEntry', padding=2)
        self.style.configure('Custom.TCombobox', padding=2)
        
        # Create main frame with padding
        main_frame = ttk.Frame(root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Input fields frame
        input_frame = ttk.Frame(main_frame)
        input_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Create input fields with proper spacing and alignment
        self.create_labeled_input(input_frame, "API TOKEN", 
                                default="zlm2XyjwUTq2nKk1QJM0TB4t0hP0j5RepYyyz9HdbZUEXcPKLaTtHjjfhzf9", 
                                row=0)
        self.create_labeled_input(input_frame, "VALUE BET THRESHOLD", default="11.57", row=1)
        self.create_labeled_input(input_frame, "BETFAIR COMMISSION", default="6.52", row=2)
        self.create_labeled_input(input_frame, "BETFAIR DISCOUNT", default="20", row=3)
        self.create_labeled_input(input_frame, "BET UNIT", default="8", row=4)
        
        # Buttons frame
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(button_frame, text="GET VALUE BET LIST", 
                  command=self.get_value_bets).pack(side=tk.LEFT, padx=2)
        ttk.Button(button_frame, text="EXPORT TO CSV",
                  command=self.export_to_csv).pack(side=tk.LEFT, padx=2)
        
        # Create Treeview with frame
        tree_frame = ttk.Frame(main_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create Treeview with proper scroll configuration
        self.create_treeview(tree_frame)
        
        # Status bar
        self.status_var = tk.StringVar()
        self.status_bar = ttk.Label(root, textvariable=self.status_var, 
                                  relief=tk.SUNKEN, anchor=tk.W, wraplength=780)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.update_status('Application initialized successfully.')

    def create_labeled_input(self, parent, label, default="", row=0):
        """Create labeled input field"""
        label_widget = ttk.Label(parent, text=label, style='Header.TLabel')
        label_widget.grid(row=row, column=0, sticky=tk.W, pady=2)
        
        var = tk.StringVar(value=default)
        widget = ttk.Entry(parent, textvariable=var, width=32, style='Custom.TEntry')
        widget.grid(row=row, column=1, sticky=tk.W, pady=2)
        var_name = label.lower().replace(' ', '_')
        setattr(self, var_name, var)
        return var

    def create_treeview(self, parent):
        """Create and configure the Treeview"""
        columns = ('event', 'betfair_adjust', 'true_odds', 'value', 'k_factor', 'money_to_bet')
        self.tree = ttk.Treeview(parent, columns=columns, show='headings', height=15)
        
        headings = ('EVENT', 'BETFAIR ADJUST', 'TRUE ODDS', 'VALUE', 'K FACTOR', 'MONEY TO BET')
        widths = [300, 100, 100, 100, 100, 100]
        
        for col, heading, width in zip(columns, headings, widths):
            self.tree.heading(col, text=heading)
            self.tree.column(col, width=width)
        
        # Add scrollbars
        y_scrollbar = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=self.tree.yview)
        x_scrollbar = ttk.Scrollbar(parent, orient=tk.HORIZONTAL, command=self.tree.xview)
        
        self.tree.configure(yscrollcommand=y_scrollbar.set, xscrollcommand=x_scrollbar.set)
        
        # Grid layout for treeview and scrollbars
        self.tree.grid(row=0, column=0, sticky='nsew')
        y_scrollbar.grid(row=0, column=1, sticky='ns')
        x_scrollbar.grid(row=1, column=0, sticky='ew')
        
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(0, weight=1)

    def update_status(self, message):
        """Update status bar with message"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.status_var.set(f'[{timestamp}] {message}')
        logger.info(message)

    def calculate_betfair_adjust(self, odds):
        """Calculate adjusted Betfair odds considering commission and discount"""
        commission = float(self.betfair_commission.get()) / 100
        discount = float(self.betfair_discount.get()) / 100
        return round(1 + (odds - 1) * (1 - commission * (1 - discount)), 2)

    def process_prediction(self, prediction):
        """Process a prediction and return structured data"""
        pred_type = prediction['type']['code']
        if pred_type not in self.PREDICTION_TYPES:
            return None
        
        fixture = prediction['fixture']
        event_name = fixture['name']
        
        results = []
        for key, label in self.PREDICTION_TYPES[pred_type].items():
            if key in prediction['predictions']:
                probability = float(prediction['predictions'][key])
                if probability > 0:
                    true_odds = 100 / probability
                    results.append({
                        'event': f"{event_name} ({label})",
                        'true_odds': true_odds,
                        'probability': probability
                    })
        
        return results

    def get_value_bets(self):
        """Process predictions and find value bets"""
        try:
            # Clear existing items
            for item in self.tree.get_children():
                self.tree.delete(item)
            
            api_token = self.api_token.get()
            value_threshold = float(self.value_bet_threshold.get())
            bet_unit = float(self.bet_unit.get())
            
            url = "https://api.sportmonks.com/v3/football/predictions/probabilities"
            params = {
                "api_token": api_token,
                "include": "type;fixture"
            }
            
            self.update_status("Fetching predictions...")
            response = requests.get(url, params=params)
            data = response.json()
            
            predictions = data.get('data', [])
            value_bets_found = 0
            
            for prediction in predictions:
                processed_data = self.process_prediction(prediction)
                if not processed_data:
                    continue
                
                for bet in processed_data:
                    true_odds = bet['true_odds']
                    # Simulating Betfair odds (in real app, you'd get these from Betfair API)
                    betfair_odds = true_odds * 0.95  # Example calculation
                    
                    betfair_adjust = self.calculate_betfair_adjust(betfair_odds)
                    value = ((betfair_adjust / true_odds) - 1) * 100
                    
                    if abs(value) >= value_threshold:
                        k_factor = true_odds  # K-factor equals true odds
                        money_to_bet = bet_unit * k_factor
                        
                        tag = 'positive' if value > 0 else 'negative'
                        self.tree.insert('', tk.END, values=(
                            bet['event'],
                            f"{betfair_adjust:.2f}",
                            f"{true_odds:.2f}",
                            f"{value:.2f}%",
                            f"{k_factor:.2f}",
                            f"{money_to_bet:.2f}"
                        ), tags=(tag,))
                        value_bets_found += 1
            
            # Configure tag colors
            self.tree.tag_configure('positive', background='#90EE90')  # Light green
            self.tree.tag_configure('negative', background='#FFB6C1')  # Light red
            
            self.update_status(f"Found {value_bets_found} value bets")
            
        except Exception as e:
            error_msg = f"Error processing data: {str(e)}"
            self.update_status(error_msg)
            messagebox.showerror("Error", error_msg)

    def export_to_csv(self):
        """Export value bets to CSV in BF Botmanager format"""
        filename = filedialog.asksaveasfilename(
            defaultextension='.csv',
            filetypes=[("CSV files", "*.csv")]
        )
        if filename:
            try:
                with open(filename, 'w', newline='', encoding='utf-8') as file:
                    writer = csv.writer(file)
                    writer.writerow([
                        "Date", "Time", "Event", "Market", "Selection",
                        "Back/Lay", "Odds", "Stake", "Value %", "Sport",
                        "Competition", "Market Type", "In-Play"
                    ])
                    
                    current_time = datetime.now()
                    
                    for item in self.tree.get_children():
                        values = self.tree.item(item)['values']
                        event_parts = values[0].split(' (')
                        event = event_parts[0]
                        selection = event_parts[1].rstrip(')')
                        
                        writer.writerow([
                            current_time.strftime("%Y-%m-%d"),
                            current_time.strftime("%H:%M"),
                            event,
                            "Match Odds",
                            selection,
                            "Back",
                            values[1],  # Betfair adjusted odds
                            values[5],  # Money to bet
                            values[3].rstrip('%'),  # Value %
                            "Football",
                            "",
                            "Match Odds",
                            "false"
                        ])
                
                self.update_status(f"Successfully exported to {filename}")
                
            except Exception as e:
                error_msg = f"Error exporting to CSV: {str(e)}"
                self.update_status(error_msg)
                messagebox.showerror("Export Error", error_msg)

def main():
    root = tk.Tk()
    app = ValueBetFinder(root)
    root.mainloop()

if __name__ == "__main__":
    main()