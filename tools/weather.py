# tools/weather.py
"""
Weather Tools - Wrapper untuk operasi cuaca menggunakan MCP API Server
"""

from typing import Optional, Dict, Any


class WeatherTools:
    """Wrapper untuk operasi cuaca"""
    
    def __init__(self, api_server, verbose: bool = False):
        """
        Inisialisasi weather tools
        
        Args:
            api_server: Instance APIServer
            verbose: Mode verbose
        """
        # STATUS: OK - Constructor berjalan normal
        self.server = api_server
        self.verbose = verbose
        
        if self.verbose:
            print("[DEBUG] WeatherTools initialized")

    def current(self, city: str, country: Optional[str] = None, units: str = 'metric') -> Dict[str, Any]:
        """Cuaca terkini"""
        # STATUS: OK - Method berjalan normal
        return self.server.weather(city, country, units)

    def forecast(self, city: str, country: Optional[str] = None, days: int = 5, units: str = 'metric') -> Dict[str, Any]:
        """Forecast cuaca"""
        # STATUS: OK - Method berjalan normal
        return self.server.weather_forecast(city, country, days, units)

    def temperature(self, city: str, country: Optional[str] = None, units: str = 'metric') -> Optional[float]:
        """Ambil suhu saja"""
        # STATUS: OK - Method berjalan normal
        result = self.server.weather(city, country, units)
        return result.get('temperature') if 'error' not in result else None

    def description(self, city: str, country: Optional[str] = None) -> Optional[str]:
        """Ambil deskripsi cuaca saja"""
        # STATUS: OK - Method berjalan normal
        result = self.server.weather(city, country)
        return result.get('description') if 'error' not in result else None


# Placeholder untuk testing
if __name__ == "__main__":
    print("=" * 50)
    print("TESTING WEATHER TOOLS")
    print("=" * 50)
    
    from mcp.api_server import APIServer
    
    # Tanpa API key (akan gagal, tapi test struktur)
    server = APIServer(verbose=False)
    tools = WeatherTools(server, verbose=True)
    
    print("\n[TEST] Get weather (without API key)")
    result = tools.current("Jakarta")
    print(f"Result: {result}")
    
    print("\n[TEST] Get temperature (without API key)")
    temp = tools.temperature("Jakarta")
    print(f"Temperature: {temp}")
    
    print("\n" + "=" * 50)
    print("STATUS: OK - Struktur siap digunakan")
    print("Catatan: Testing membutuhkan API key untuk hasil aktual")
    print("=" * 50)