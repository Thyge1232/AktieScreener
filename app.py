import streamlit as st

st.set_page_config(
    page_title="Investment Screener Hub",
    layout="wide"
)

st.title("Velkommen til din Investment Screener Hub")
st.markdown("---")
st.header("Vælg en screener i menuen til venstre for at starte.")

st.info(
    """
    - **Multibagger Screener:** Fokuserer på at finde selskaber med potentiale for eksplosiv vækst.
    - **Value Screener:** Fokuserer på at finde undervurderede selskaber baseret på klassiske værdi-principper.
    """
)