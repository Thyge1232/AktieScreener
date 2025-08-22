# ai_analyzer.py
import requests

def generate_with_ollama(model_name, prompt):
    """
    Brug Ollama REST API til at generere tekst
    """
    try:
        response = requests.post(
            'http://localhost:11434/api/generate',
            json={
                "model": model_name,
                "prompt": prompt,
                "stream": False
            },
            timeout=30
        )
        
        if response.status_code == 200:
            return response.json()['response']
        else:
            return f"Fejl: {response.status_code} - {response.text}"
            
    except requests.exceptions.RequestException as e:
        return f"Netværksfejl: {e}"

# Testeksempel
if __name__ == "__main__":
    result = generate_with_ollama("codellama:7b", "Analyze this stock data: P/E=15, ROIC=20%, Debt/Equity=0.5")
    print(result)