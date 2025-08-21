# Fil: utils/validation.py

import streamlit as st
import pandas as pd
import numpy as np
from st_aggrid import AgGrid

def validate_screening_data(df, profile_config):
    """
    Validerer datakvaliteten for den valgte profil før screening.
    Denne funktion er generisk og kan bruges af enhver screener.
    """
    validation_errors = []
    warnings = []
    
    # 1. Tjek for nødvendige kolonner baseret på profilen
    required_cols = set()
    for filter_details in profile_config.get('filters', {}).values():
        if 'data_key' in filter_details:
            required_cols.add(filter_details['data_key'])
    
    missing_cols = required_cols - set(df.columns)
    if missing_cols:
        validation_errors.append(f"Din CSV-fil mangler påkrævede kolonner for denne profil: **{', '.join(missing_cols)}**")
    
    # Fortsæt kun yderligere tjek, hvis kolonnerne findes
    if not validation_errors:
        # 2. Tjek for høj andel af manglende data
        for col in required_cols:
            if col in df.columns:
                missing_pct = (df[col].isnull().sum() / len(df)) * 100
                if missing_pct > 75: # Sæt en høj tærskel
                    warnings.append(f"Kolonnen **'{col}'** har {missing_pct:.0f}% manglende værdier, hvilket kan påvirke scoringen.")

    return validation_errors, warnings

def safe_aggrid_display(df_for_grid, grid_options, grid_key):
    """
    Sikker AgGrid visning med fejlhåndtering og dynamisk højde.
    Denne funktion er generisk og kan bruges på alle sider med en AgGrid-tabel.
    """
    try:
        # Beregn dynamisk højde: 35px pr. række + 100px for header/padding
        dynamic_height = min(600, len(df_for_grid) * 35 + 100)
        
        return AgGrid(
            df_for_grid, 
            gridOptions=grid_options, 
            key=grid_key,
            allow_unsafe_jscode=True, 
            theme="streamlit-dark", 
            fit_columns_on_grid_load=True, 
            height=dynamic_height,
            update_on=['cellValueChanged']
        )
    except Exception as e:
        st.error(f"Fejl under opbygning af interaktiv tabel: {str(e)}")
        st.info("Viser en simpel fallback-tabel:")
        st.dataframe(df_for_grid) # Vis en simpel, ikke-interaktiv tabel som fallback
        return None # Returner None for at signalere en fejl