# core/backtesting/strategy_engine.py
import pandas as pd
import numpy as np
import streamlit as st
import time
from datetime import datetime, timedelta

class SimpleBacktester:
    def __init__(self, initial_capital=10000):
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.positions = {}
        self.portfolio_history = []
        
    def calculate_sma(self, prices, window):
        """Simpelt glidende gennemsnit."""
        return prices.rolling(window=window).mean()
    
    def moving_average_strategy(self, df, short_window=20, long_window=50):
        """
        Simpel moving average crossover strategi.
        Køb når kort MA krydser over lang MA, sælg ved omvendt.
        """
        results = []
        
        for ticker in df['Ticker'].unique():
            ticker_data = df[df['Ticker'] == ticker].copy()
            
            # Beregn moving averages
            ticker_data['SMA_Short'] = self.calculate_sma(ticker_data['Adjusted_Close'], short_window)
            ticker_data['SMA_Long'] = self.calculate_sma(ticker_data['Adjusted_Close'], long_window)
            
            # Generer signaler
            ticker_data['Signal'] = 0
            ticker_data['Signal'][short_window:] = np.where(
                ticker_data['SMA_Short'][short_window:] > ticker_data['SMA_Long'][short_window:], 1, -1
            )
            
            # Beregn positionsændringer
            ticker_data['Position'] = ticker_data['Signal'].diff()
            
            # Beregn returns
            ticker_data['Returns'] = ticker_data['Adjusted_Close'].pct_change()
            ticker_data['Strategy_Returns'] = ticker_data['Returns'] * ticker_data['Signal'].shift(1)
            
            # Kumulativt afkast
            ticker_data['Cumulative_Returns'] = (1 + ticker_data['Strategy_Returns']).cumprod()
            ticker_data['Buy_Hold_Returns'] = (1 + ticker_data['Returns']).cumprod()
            
            results.append(ticker_data)
        
        return pd.concat(results, ignore_index=False)
    
    def value_strategy_backtest(self, historical_data, fundamental_data, pe_threshold=15, market_cap_min=1e9):
        """
        Backtest af value-strategi baseret på P/E ratio og market cap.
        """
        # Filtrer aktier baseret på value-kriterier
        value_stocks = []
        for _, stock in fundamental_data.iterrows():
            ticker = stock['Ticker']
            pe_ratio = stock['P/E']
            market_cap = stock['Market Cap']
            
            if (pd.notna(pe_ratio) and pe_ratio < pe_threshold and 
                pd.notna(market_cap) and market_cap > market_cap_min):
                value_stocks.append(ticker)
        
        if not value_stocks:
            return pd.DataFrame(), "Ingen aktier matchede value-kriterierne"
        
        # Backtest kun på value-aktier
        filtered_data = historical_data[historical_data['Ticker'].isin(value_stocks)]
        
        if filtered_data.empty:
            return pd.DataFrame(), "Ingen historiske data for value-aktier"
        
        # Simpel buy-and-hold for value-aktier
        results = []
        equal_weight = 1.0 / len(value_stocks)
        
        for ticker in value_stocks:
            ticker_data = filtered_data[filtered_data['Ticker'] == ticker].copy()
            if not ticker_data.empty:
                ticker_data['Returns'] = ticker_data['Adjusted_Close'].pct_change()
                ticker_data['Weighted_Returns'] = ticker_data['Returns'] * equal_weight
                ticker_data['Cumulative_Returns'] = (1 + ticker_data['Returns']).cumprod()
                results.append(ticker_data)
        
        if results:
            combined_results = pd.concat(results, ignore_index=False)
            return combined_results, f"Backtest gennemført for {len(value_stocks)} value-aktier"
        else:
            return pd.DataFrame(), "Kunne ikke gennemføre backtest"
    
    def calculate_metrics(self, returns_series):
        """Beregn performance-metrics."""
        if returns_series.empty or returns_series.isna().all():
            return {}
        
        total_return = (1 + returns_series).prod() - 1
        annualized_return = (1 + total_return) ** (252 / len(returns_series)) - 1
        volatility = returns_series.std() * np.sqrt(252)
        sharpe_ratio = annualized_return / volatility if volatility > 0 else 0
        
        # Max drawdown
        cumulative = (1 + returns_series).cumprod()
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max
        max_drawdown = drawdown.min()
        
        return {
            'Total Return': f"{total_return:.2%}",
            'Annualized Return': f"{annualized_return:.2%}",
            'Volatility': f"{volatility:.2%}",
            'Sharpe Ratio': f"{sharpe_ratio:.2f}",
            'Max Drawdown': f"{max_drawdown:.2%}"
        }