import requests
from datetime import datetime, timedelta
import json
import yfinance as yf
import matplotlib.pyplot as plt

API_KEY = 'Alpha Vantage API here'
user_accounts = {}


def plot_stock_data(symbol, time_period='1y'):
    if time_period == '1w':
        start_date = (datetime.now() - timedelta(weeks=1)).strftime('%Y-%m-%d')
    elif time_period == '6m':
        start_date = (datetime.now() - timedelta(days=180)).strftime('%Y-%m-%d')
    else:
        start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')

    stock = yf.Ticker(symbol)
    historical_data = stock.history(period=time_period)

    if not historical_data.empty:
        dates = historical_data.index
        prices = historical_data['Close'].tolist()

        plt.figure(figsize=(12, 6))
        plt.plot(dates, prices, label=symbol)
        plt.title(f'{symbol} Stock Prices Over Time')
        plt.xlabel('Date')
        plt.ylabel('Price')
        plt.legend()
        plt.show()
    else:
        print(f"No historical data available for {symbol} in the selected time period.")


class User:
    def __init__(self, username, password, initial_balance=10000):
        self.username = username
        self.password = password
        self.portfolio_manager = PortfolioManager(username, initial_balance)
        user_accounts[username] = self
        self.save_user_to_file()

    def save_user_to_file(self):
        user_data = {
            "username": self.username,
            "password": self.password,
            "portfolio_manager": self.portfolio_manager.__dict__,
        }
        with open(f'{self.username}_user.json', 'w') as file:
            json.dump(user_data, file)



class PortfolioManager:
    def __init__(self, username, initial_balance, filename='portfolio.json', stock_data_filename='stock_data.json'):
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.username = username
        self.filename = f'{self.username}_{filename}'  # Use a username-specific filename
        self.stock_data_filename = f'{self.username}_{stock_data_filename}'
        self.portfolio = self.load_portfolio_from_file()
        self.stock_data = self.load_stock_data_from_file()
        self.transactions = self.load_transaction_history_from_file()

    def load_portfolio_from_file(self):
        try:
            with open(self.filename, 'r') as file:
                data = json.load(file)
                return data
        except FileNotFoundError:
            return {}

    def load_stock_data_from_file(self):
        try:
            with open(self.stock_data_filename, 'r') as file:
                data = json.load(file)
                return data
        except FileNotFoundError:
            return {}

    def save_portfolio_to_file(self):
        with open(self.filename, 'w') as file:
            json.dump(self.portfolio, file)

    def save_stock_data_to_file(self):
        with open(self.stock_data_filename, 'w') as file:
            json.dump(self.stock_data, file)

    def load_transaction_history_from_file(self):
        try:
            with open(f'{self.username}_transaction_history.json', 'r') as file:
                data = json.load(file)
                return data
        except FileNotFoundError:
            return []

    def save_transaction_history_to_file(self):
        with open(f'{self.username}_transaction_history.json', 'w') as file:
            json.dump(self.transactions, file)

    def update_portfolio(self):
        self.save_portfolio_to_file()
        self.save_transaction_history_to_file()

    def get_portfolio_value(self):
        total_value = 0.0
        for symbol, data in self.portfolio.items():
            if data['amount'] > 0:
                stock = yf.Ticker(symbol)
                current_price = stock.history(period="1d")["Close"].values[0]
                total_value += data['amount'] * current_price
        return total_value

    def buy_stock(self, symbol, amount, price):
        if symbol in self.portfolio:
            self.portfolio[symbol]['amount'] += amount
            self.portfolio[symbol]['money_spent'] += amount * price
        else:
            self.portfolio[symbol] = {'amount': amount, 'money_spent': amount * price}

        total_cost = amount * price
        if total_cost <= self.balance:
            self.balance -= total_cost
            self.transactions.append({'action': 'BUY', 'symbol': symbol, 'amount': amount, 'price': price})
            self.update_portfolio()
        else:
            print("Insufficient balance to buy this stock.")

    def sell_stock(self, symbol, amount, price):
        if symbol in self.portfolio and self.portfolio[symbol]['amount'] >= amount:
            self.portfolio[symbol]['amount'] -= amount
            self.portfolio[symbol]['money_spent'] -= amount * price
            self.transactions.append({'action': 'SELL', 'symbol': symbol, 'amount': amount, 'price': price})
            self.update_portfolio()
        else:
            print(f"You don't have enough {symbol} stocks to sell.")

    def print_portfolio(self):
        portfolio_text = "Your Portfolio:\n"
        for symbol, data in self.portfolio.items():
            portfolio_text += f"{symbol}: Amount - {data['amount']}, Money Spent - {data['money_spent']:.2f}\n"
        print(portfolio_text)

    def print_transaction_history(self):
        print("\nTransaction History:")
        for transaction in self.transactions:
            action = transaction['action']
            symbol = transaction['symbol']
            amount = transaction['amount']
            price = transaction['price']
            print(f"{action} {amount} shares of {symbol} at ${price:.2f} each")

    def get_stock_prices(self, symbol):
        if symbol in self.stock_data:
            data = self.stock_data[symbol]
            dates = [datetime.strptime(date, '%Y-%m-%d') for date in data['dates']]
            prices = [float(price) for price in data['prices']]
            return dates, prices

        base_url = 'https://www.alphavantage.co/query'
        params = {
            'function': 'TIME_SERIES_DAILY',
            'symbol': symbol,
            'apikey': API_KEY
        }

        try:
            response = requests.get(base_url, params=params)
            data = response.json()

            if 'Time Series (Daily)' in data:
                historical_data = data['Time Series (Daily)']
                dates = []
                prices = []

                for date, info in historical_data.items():
                    dates.append(datetime.strptime(date, '%Y-%m-%d'))
                    prices.append(float(info['4. close']))

                self.stock_data[symbol] = {'dates': [date.strftime('%Y-%m-%d') for date in dates],
                                           'prices': [str(price) for price in prices]}
                self.save_stock_data_to_file()

                return dates, prices

        except Exception as e:
            print(f"An error occurred: {e}")
            return None, None


def buy_stock_cmd(user):
    symbol = input("Enter stock symbol: ").strip().upper()
    amount = int(input("Enter amount to buy: "))
    dates, prices = user.portfolio_manager.get_stock_prices(symbol)
    if dates and prices:
        user.portfolio_manager.buy_stock(symbol, amount, prices[-1])
    else:
        print(f"Failed to buy {symbol} stock.")

def sell_stock_cmd(user):
    symbol = input("Enter stock symbol to sell: ").strip().upper()
    amount = int(input("Enter amount to sell: "))
    if symbol in user.portfolio_manager.portfolio and user.portfolio_manager.portfolio[symbol]['amount'] >= amount:
        dates, prices = user.portfolio_manager.get_stock_prices(symbol)
        if dates and prices:
            user.portfolio_manager.sell_stock(symbol, amount, prices[-1])
    else:
        print(f"You don't have enough {symbol} stocks to sell.")


def create_account():
    username = input("Enter a username: ")
    if username in user_accounts:
        print("Username already exists. Please choose a different one.")
        return
    password = input("Enter a password: ")
    user = User(username, password)
    print("Account created successfully.")


def login():
    username = input("Enter your username: ")
    password = input("Enter your password: ")

    if username not in user_accounts:
        print("Username not found. Please try again.")
    elif user_accounts[username].password != password:
        print("Invalid password. Please try again.")
    else:
        print(f"Welcome, {username}!")
        main_menu(user_accounts[username])

def main_menu(user):
    while True:
        print("\nStock Portfolio Management")
        print("1. Buy Stock")
        print("2. Sell Stock")
        print("3. View Portfolio")
        print("4. View Transaction History")
        print("5. View Portfolio Value")
        print("6. Quit")
        print("7. Plot Stock Data")
        choice = input("Enter your choice: ")
        if choice == '1':
            buy_stock_cmd(user)
        elif choice == '2':
            sell_stock_cmd(user)
        elif choice == '3':
            user.portfolio_manager.print_portfolio()
        elif choice == '4':
            user.portfolio_manager.print_transaction_history()
        elif choice == '5':
            portfolio_value = user.portfolio_manager.get_portfolio_value()
            print(f"Portfolio Value: ${portfolio_value:.2f}")
        elif choice == '6':
            print("Exiting the program.")
            break
        elif choice == '7':
            symbol = input("Enter stock symbol to plot: ").strip().upper()
            time_period = input("Select time period (1y, 6m, 1w): ")
            plot_stock_data(symbol, time_period)
        else:
            print("Invalid choice. Please try again.")


if __name__ == "__main__":

    while True:
        print("\nStock Portfolio Management")
        print("1. Create Account")
        print("2. Login")
        print("3. Quit")
        choice = input("Enter your choice: ")

        if choice == '1':
            create_account()
        elif choice == '2':
            login()
        elif choice == '3':
            print("Exiting the program.")
            break
        else:
            print("Invalid choice. Please try again.")
