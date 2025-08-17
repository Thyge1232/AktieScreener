import streamlit as st
from core.data.data_fetcher import get_all_listed_stocks, fetch_stock_data_av
from core.screening.multibagger_screener import screen_stocks

st.title("🚀 Automatisk Multibagger Screener")

profile = st.selectbox("Vælg profil:", ["Stram", "Løs", "Momentum"])

if st.button("Start Fuld Markedsscanning"):
    with st.spinner("Henter liste over aktier..."):
        tickers = get_all_listed_stocks()
        st.info(f"Fandt {len(tickers)} aktier. Starter screening...")

    results = []
    progress = st.progress(0)

    for i, ticker in enumerate(tickers):
        data = fetch_stock_data_av(ticker)
        if data:
            score, passes = screen_stocks(data, profile)
            if passes:
                results.append({"Ticker": ticker, "Score": score, **data})
        progress.progress((i + 1) / len(tickers))

    st.success("Scanning færdig!")
    st.dataframe(results)