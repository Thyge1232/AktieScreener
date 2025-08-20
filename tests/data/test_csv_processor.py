# tests/data/test_csv_processor.py

import pandas as pd
import numpy as np
import pytest
import io

# Importer de funktioner fra din fil, som vi skal teste
from core.data.csv_processor import (
    parse_market_cap,
    find_column_name,
    process_finviz_csv
)

# ======================================================================
#  UNIT TESTS FOR HJÆLPEFUNKTIONER (Disse er uændrede og gode at have)
# ======================================================================

@pytest.mark.parametrize("input_str, expected_value", [
    ('2.5B', 2_500_000_000),
    ('500M', 500_000_000),
    ('33734.10', 33734100000.0),  # Test for tal uden suffix (antaget som millioner)
    ('-', None)
])
def test_parse_market_cap(input_str, expected_value):
    """Tester parse_market_cap med forskellige formater."""
    result = parse_market_cap(input_str)
    if expected_value is None:
        assert pd.isna(result)
    else:
        assert result == expected_value

def test_find_column_name():
    """Tester find_column_name for at finde korrekte kolonnenavne."""
    df = pd.DataFrame(columns=['Ticker', 'Price', 'Book/sh'])
    assert find_column_name(df, ['Price', 'Close']) == 'Price'
    assert find_column_name(df, ['Close', 'Book/sh']) == 'Book/sh'
    assert find_column_name(df, ['Market Cap']) is None

# ======================================================================
#  INTEGRATION TEST FOR HOVEDFUNKTIONEN (med korrekt formateret input)
# ======================================================================

@pytest.fixture
def correctly_formatted_csv_fixture():
    """
    Laver en fixture, der simulerer en PERFEKT formateret CSV-fil i hukommelsen,
    som din process_finviz_csv forventer at modtage.
    """
    # Header og data er standard CSV, adskilt af kommaer.
    # Dette er det format, pd.read_csv(..., sep=',') vil producere internt.
    csv_data = (
        '"No.","Ticker","Company","Market Cap","P/E","Dividend Yield","Insider Transactions","Price","Book/sh","Change"\n'
        '"1","A","Agilent","33734.10","29.29","0.83%","-1.27%","118.75","21.61","-0.37%"\n'
        '"2","B","Barnes Group","-","15.0","1.50%","5.00%","50.00","0","2.00%"'
    )
    
    # Returner som et fil-lignende objekt
    return io.StringIO(csv_data)


def test_process_csv_with_correctly_formatted_input(correctly_formatted_csv_fixture):
    """
    Tester om process_finviz_csv korrekt kan parse en fil, der er korrekt formateret.
    """
    # Kald funktionen med vores simulerede, korrekte fil
    df = process_finviz_csv(correctly_formatted_csv_fixture)
    
    # --- Assertion 1: Tjek at data er indlæst og har korrekt størrelse ---
    assert not df.empty
    assert len(df) == 2
    
    # --- Assertion 2: Tjekker værdierne for den første række (Agilent) ---
    agilent_row = df[df['Ticker'] == 'A'].iloc[0]
    
    # Tjek Market Cap (nummer uden suffix antages at være millioner af parse_market_cap)
    assert agilent_row['Market Cap'] == 33734.10 * 1_000_000
    
    # Tjek en standard numerisk kolonne
    assert agilent_row['P/E'] == 29.29
    
    # Tjek procent-kolonner
    assert agilent_row['Dividend Yield'] == pytest.approx(0.0083)
    assert agilent_row['Insider Transactions'] == pytest.approx(-0.0127)
    
    # Tjek den afledte metrik
    assert 'Price vs. Book/sh' in df.columns
    expected_pb = 118.75 / 21.61
    assert agilent_row['Price vs. Book/sh'] == pytest.approx(expected_pb)

    # --- Assertion 3: Tjekker værdier for den anden række (Barnes Group) ---
    barnes_row = df[df['Ticker'] == 'B'].iloc[0]
    
    # Tjek håndtering af manglende værdi ('-')
    assert pd.isna(barnes_row['Market Cap'])
    
    # Tjek håndtering af ugyldig Book/sh (0) for den afledte metrik
    assert pd.isna(barnes_row['Price vs. Book/sh'])

    # --- Assertion 4: Tjek datatyper for hele kolonner ---
    assert pd.api.types.is_numeric_dtype(df['Market Cap'])
    assert pd.api.types.is_numeric_dtype(df['P/E'])
    assert pd.api.types.is_numeric_dtype(df['Change'])
    assert pd.api.types.is_object_dtype(df['Ticker'])