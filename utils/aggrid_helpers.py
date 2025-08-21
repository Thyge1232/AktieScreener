# utils/aggrid_helpers.py

from st_aggrid import JsCode

# --- Cell Renderers (for interaktive elementer som knapper og links) ---

# Renderer for favorit-knappen (⭐/➕)
JS_FAVORITE_CELL_RENDERER = JsCode("""
class FavoriteCellRenderer {
    init(params) {
        this.params = params;
        this.eGui = document.createElement('div');
        this.eGui.style.cssText = 'text-align: center; cursor: pointer; font-size: 1.2em;';
        this.eGui.innerHTML = params.value ? "⭐" : "➕"; // Sæt det korrekte ikon fra start
        
        this.eGui.addEventListener('click', () => {
            // Send den modsatte værdi tilbage til Python for at signalere et klik
            this.params.node.setDataValue('is_favorite', !this.params.value);
        });
    }

    getGui() { return this.eGui; }

    // Refresh kaldes af AgGrid, når data ændres, og sikrer at ikonet opdateres korrekt.
    refresh(params) {
        this.params = params;
        this.eGui.innerHTML = params.value ? "⭐" : "➕";
        return true;
    }
}
""")

# Renderer for at gøre Ticker-symbolet til et klikbart link til Finviz
JS_TICKER_LINK_RENDERER = JsCode("""
class TickerLinkRenderer {
    init(params) {
        this.eGui = document.createElement('a');
        this.eGui.innerText = params.value;
        this.eGui.href = `https://finviz.com/quote.ashx?t=${params.value}&ty=l&ta=0&p=w&r=y2`;
        this.eGui.target = '_blank'; // Åbn i ny fane
        this.eGui.style.cssText = 'color: #ADD8E6; text-decoration: underline;';
    }
    getGui() { return this.eGui; }
}
""")


# --- Value Formatters (for at formatere tal, valuta, procenter etc.) ---

# Formaterer store tal til en læsbar Market Cap (f.eks. 1.2B for 1,200,000,000)
JS_MARKET_CAP_FORMATTER = JsCode("""
function(params) {
    if (params.value == null || isNaN(params.value)) return '-';
    const num = parseFloat(params.value);
    if (num < 1e9) return '$' + (num / 1e6).toFixed(1) + 'M';
    if (num < 1e12) return '$' + (num / 1e9).toFixed(2) + 'B';
    return '$' + (num / 1e12).toFixed(2) + 'T';
}
""")

# Formaterer et tal til en pris i USD med to decimaler
JS_PRICE_FORMATTER = JsCode("""
function(params) {
    return params.value != null && !isNaN(params.value) ? '$' + parseFloat(params.value).toFixed(2) : '-';
}
""")

# Formaterer et tal til en score med ét decimal og et procenttegn
JS_SCORE_FORMATTER = JsCode("""
function(params) {
    return params.value != null && !isNaN(params.value) ? parseFloat(params.value).toFixed(1) + '%' : '-';
}
""")

# Formaterer et decimaltal (f.eks. 0.25) til en procentstreng (f.eks. "25.0%")
JS_PERCENTAGE_FORMATTER = JsCode("""
function(params) {
    return params.value != null && !isNaN(params.value) ? (parseFloat(params.value) * 100).toFixed(1) + '%' : '-';
}
""")

# Formaterer et tal til en streng med to decimaler
JS_TWO_DECIMAL_FORMATTER = JsCode("""
function(params) {
    return params.value != null && !isNaN(params.value) ? parseFloat(params.value).toFixed(2) : '-';
}
""")


# --- Grid/Row Styling ---

# Giver rækker en gullig baggrund, hvis de er markeret som favorit
JS_FAVORITE_ROW_STYLE = JsCode("""
function(params) {
    if (params.data.is_favorite) {
        return { 'backgroundColor': 'rgba(255, 255, 0, 0.1)' };
    }
}
""")