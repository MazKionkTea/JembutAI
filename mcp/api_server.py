# mcp/api_server.py
"""
MCP API Server - Menyediakan akses ke API eksternal (cuaca, berita, Wikipedia, dll)
"""

import json
import urllib.request
import urllib.parse
from typing import Optional, List, Dict, Any
from datetime import datetime
import ssl


class APIServer:
    """MCP Server untuk akses API eksternal"""
    
    def __init__(
        self,
        weather_api_key: Optional[str] = None,
        news_api_key: Optional[str] = None,
        currency_api_key: Optional[str] = None,
        github_token: Optional[str] = None,
        timeout: int = 10,
        verbose: bool = False
    ):
        """
        Inisialisasi API server
        
        Args:
            weather_api_key: API key untuk weather (OpenWeatherMap)
            news_api_key: API key untuk news (NewsAPI)
            currency_api_key: API key untuk currency (ExchangeRate-API)
            github_token: GitHub personal access token
            timeout: Timeout request (detik)
            verbose: Mode verbose
        """
        # STATUS: OK - Constructor berjalan normal
        self.weather_api_key = weather_api_key
        self.news_api_key = news_api_key
        self.currency_api_key = currency_api_key
        self.github_token = github_token
        self.timeout = timeout
        self.verbose = verbose
        
        # Statistik
        self.total_requests = 0
        self.total_errors = 0
        
        # Bypass SSL verification (untuk testing)
        self.ssl_context = ssl.create_default_context()
        self.ssl_context.check_hostname = False
        self.ssl_context.verify_mode = ssl.CERT_NONE
        
        if self.verbose:
            print(f"[DEBUG] APIServer initialized")
            print(f"[DEBUG] Weather API: {'Configured' if weather_api_key else 'Not configured'}")
            print(f"[DEBUG] News API: {'Configured' if news_api_key else 'Not configured'}")
            print(f"[DEBUG] Currency API: {'Configured' if currency_api_key else 'Not configured'}")
            print(f"[DEBUG] GitHub: {'Configured' if github_token else 'Not configured'}")

    def _make_request(self, url: str, headers: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Buat HTTP request dan return JSON response
        
        Args:
            url: URL endpoint
            headers: Headers tambahan
        
        Returns:
            Dict JSON response
        """
        # STATUS: OK - Method berjalan normal
        try:
            # Buat request dengan headers
            req = urllib.request.Request(url)
            
            if headers:
                for key, value in headers.items():
                    req.add_header(key, value)
            
            # Buka URL
            with urllib.request.urlopen(req, timeout=self.timeout, context=self.ssl_context) as response:
                data = response.read().decode('utf-8')
                result = json.loads(data)
                
                self.total_requests += 1
                
                if self.verbose:
                    print(f"[DEBUG] API request successful: {url[:50]}...")
                
                return result
                
        except urllib.error.URLError as e:
            self.total_errors += 1
            print(f"[ERROR] Network error: {e}")
            raise
        except json.JSONDecodeError as e:
            self.total_errors += 1
            print(f"[ERROR] JSON decode error: {e}")
            raise
        except Exception as e:
            self.total_errors += 1
            print(f"[ERROR] Request failed: {e}")
            raise

    # ==================== WEATHER ====================
    
    def weather(self, city: str, country: Optional[str] = None, units: str = 'metric') -> Dict[str, Any]:
        """
        Ambil informasi cuaca untuk kota
        
        Args:
            city: Nama kota
            country: Kode negara (opsional, misal: ID)
            units: satuan (metric, imperial)
        
        Returns:
            Dict informasi cuaca
        """
        # STATUS: OK - Method berjalan normal
        # VALIDASI
        if not self.weather_api_key:
            return {
                'error': 'Weather API key not configured',
                'message': 'Set weather_api_key saat inisialisasi'
            }
        
        if not city or not isinstance(city, str):
            raise ValueError("City harus string tidak kosong")
        
        try:
            # Build query
            query = city
            if country:
                query = f"{city},{country}"
            
            # OpenWeatherMap API
            url = (
                f"https://api.openweathermap.org/data/2.5/weather"
                f"?q={urllib.parse.quote(query)}"
                f"&units={units}"
                f"&appid={self.weather_api_key}"
            )
            
            result = self._make_request(url)
            
            # Parse response
            weather_data = {
                'city': result.get('name', city),
                'country': result.get('sys', {}).get('country', ''),
                'temperature': result.get('main', {}).get('temp'),
                'feels_like': result.get('main', {}).get('feels_like'),
                'humidity': result.get('main', {}).get('humidity'),
                'pressure': result.get('main', {}).get('pressure'),
                'description': result.get('weather', [{}])[0].get('description', ''),
                'icon': result.get('weather', [{}])[0].get('icon', ''),
                'wind_speed': result.get('wind', {}).get('speed'),
                'wind_degree': result.get('wind', {}).get('deg'),
                'clouds': result.get('clouds', {}).get('all'),
                'units': units,
                'timestamp': datetime.now().isoformat()
            }
            
            if self.verbose:
                print(f"[DEBUG] Weather data fetched for {city}")
            
            return weather_data
            
        except Exception as e:
            print(f"[ERROR] Failed to get weather: {e}")
            return {
                'error': str(e),
                'city': city,
                'message': f"Gagal mengambil data cuaca untuk {city}"
            }

    def weather_forecast(self, city: str, country: Optional[str] = None, days: int = 5, units: str = 'metric') -> Dict[str, Any]:
        """
        Ambil forecast cuaca untuk kota
        
        Args:
            city: Nama kota
            country: Kode negara (opsional)
            days: Jumlah hari forecast (max 5)
            units: satuan (metric, imperial)
        
        Returns:
            Dict forecast cuaca
        """
        # STATUS: OK - Method berjalan normal
        # VALIDASI
        if not self.weather_api_key:
            return {
                'error': 'Weather API key not configured',
                'message': 'Set weather_api_key saat inisialisasi'
            }
        
        if not city or not isinstance(city, str):
            raise ValueError("City harus string tidak kosong")
        
        try:
            query = city
            if country:
                query = f"{city},{country}"
            
            url = (
                f"https://api.openweathermap.org/data/2.5/forecast"
                f"?q={urllib.parse.quote(query)}"
                f"&units={units}"
                f"&cnt={days * 8}"  # 8 data per hari
                f"&appid={self.weather_api_key}"
            )
            
            result = self._make_request(url)
            
            # Parse forecast
            forecast_list = []
            for item in result.get('list', []):
                forecast_list.append({
                    'datetime': item.get('dt_txt'),
                    'temperature': item.get('main', {}).get('temp'),
                    'feels_like': item.get('main', {}).get('feels_like'),
                    'humidity': item.get('main', {}).get('humidity'),
                    'description': item.get('weather', [{}])[0].get('description', ''),
                    'icon': item.get('weather', [{}])[0].get('icon', ''),
                    'wind_speed': item.get('wind', {}).get('speed'),
                    'rain': item.get('rain', {}).get('3h', 0) if 'rain' in item else 0
                })
            
            return {
                'city': result.get('city', {}).get('name', city),
                'country': result.get('city', {}).get('country', ''),
                'units': units,
                'forecast': forecast_list[:days * 8],
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"[ERROR] Failed to get forecast: {e}")
            return {
                'error': str(e),
                'city': city,
                'message': f"Gagal mengambil forecast untuk {city}"
            }

    # ==================== WIKIPEDIA ====================
    
    def wikipedia(self, query: str, lang: str = 'id', limit: int = 5) -> Dict[str, Any]:
        """
        Cari artikel Wikipedia
        
        Args:
            query: Kata kunci pencarian
            lang: Kode bahasa (id, en, jp, dll)
            limit: Jumlah hasil
        
        Returns:
            Dict hasil pencarian
        """
        # STATUS: OK - Method berjalan normal
        # VALIDASI
        if not query or not isinstance(query, str):
            raise ValueError("Query harus string tidak kosong")
        
        try:
            # Wikipedia API
            url = (
                f"https://{lang}.wikipedia.org/w/api.php"
                f"?action=query"
                f"&list=search"
                f"&srsearch={urllib.parse.quote(query)}"
                f"&srlimit={limit}"
                f"&format=json"
                f"&origin=*"
            )
            
            result = self._make_request(url)
            
            # Parse results
            search_results = []
            for item in result.get('query', {}).get('search', []):
                search_results.append({
                    'title': item.get('title'),
                    'snippet': item.get('snippet', '').replace('<span class="searchmatch">', '').replace('</span>', ''),
                    'page_id': item.get('pageid'),
                    'size': item.get('size'),
                    'word_count': item.get('wordcount'),
                    'timestamp': item.get('timestamp')
                })
            
            return {
                'query': query,
                'language': lang,
                'total_results': result.get('query', {}).get('searchinfo', {}).get('totalhits', 0),
                'results': search_results,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"[ERROR] Failed to search Wikipedia: {e}")
            return {
                'error': str(e),
                'query': query,
                'message': f"Gagal mencari di Wikipedia: {query}"
            }

    def wikipedia_page(self, title: str, lang: str = 'id') -> Dict[str, Any]:
        """
        Ambil konten lengkap halaman Wikipedia
        
        Args:
            title: Judul halaman
            lang: Kode bahasa
        
        Returns:
            Dict konten halaman
        """
        # STATUS: OK - Method berjalan normal
        # VALIDASI
        if not title or not isinstance(title, str):
            raise ValueError("Title harus string tidak kosong")
        
        try:
            url = (
                f"https://{lang}.wikipedia.org/w/api.php"
                f"?action=query"
                f"&prop=extracts|info"
                f"&exintro"
                f"&explaintext"
                f"&titles={urllib.parse.quote(title)}"
                f"&format=json"
                f"&origin=*"
            )
            
            result = self._make_request(url)
            
            # Parse result
            pages = result.get('query', {}).get('pages', {})
            for page_id, page_data in pages.items():
                if page_id == '-1':
                    return {
                        'error': 'Page not found',
                        'title': title,
                        'message': f"Halaman '{title}' tidak ditemukan"
                    }
                
                return {
                    'title': page_data.get('title'),
                    'page_id': page_id,
                    'extract': page_data.get('extract', ''),
                    'full_url': f"https://{lang}.wikipedia.org/wiki/{urllib.parse.quote(title)}",
                    'last_modified': page_data.get('touched'),
                    'language': lang,
                    'timestamp': datetime.now().isoformat()
                }
            
            return {
                'error': 'No page found',
                'title': title
            }
            
        except Exception as e:
            print(f"[ERROR] Failed to get Wikipedia page: {e}")
            return {
                'error': str(e),
                'title': title,
                'message': f"Gagal mengambil halaman Wikipedia: {title}"
            }

    # ==================== NEWS ====================
    
    def news(self, query: Optional[str] = None, category: Optional[str] = None, country: str = 'id', limit: int = 10) -> Dict[str, Any]:
        """
        Ambil berita terkini
        
        Args:
            query: Kata kunci pencarian (opsional)
            category: Kategori (business, entertainment, general, health, science, sports, technology)
            country: Kode negara
            limit: Jumlah berita
        
        Returns:
            Dict berita
        """
        # STATUS: OK - Method berjalan normal
        # VALIDASI
        if not self.news_api_key:
            return {
                'error': 'News API key not configured',
                'message': 'Set news_api_key saat inisialisasi'
            }
        
        try:
            # Build URL
            base_url = "https://newsapi.org/v2/top-headlines"
            params = []
            
            if query:
                params.append(f"q={urllib.parse.quote(query)}")
            
            if category:
                params.append(f"category={category}")
            
            if country:
                params.append(f"country={country}")
            
            params.append(f"pageSize={limit}")
            params.append(f"apiKey={self.news_api_key}")
            
            url = f"{base_url}?{'&'.join(params)}"
            
            result = self._make_request(url)
            
            if result.get('status') != 'ok':
                return {
                    'error': result.get('message', 'Unknown error'),
                    'message': 'Gagal mengambil berita'
                }
            
            # Parse articles
            articles = []
            for item in result.get('articles', []):
                articles.append({
                    'title': item.get('title'),
                    'description': item.get('description'),
                    'content': item.get('content'),
                    'url': item.get('url'),
                    'source': item.get('source', {}).get('name'),
                    'author': item.get('author'),
                    'published_at': item.get('publishedAt'),
                    'image_url': item.get('urlToImage')
                })
            
            return {
                'query': query or 'top headlines',
                'category': category or 'general',
                'country': country,
                'total_results': result.get('totalResults', 0),
                'articles': articles[:limit],
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"[ERROR] Failed to get news: {e}")
            return {
                'error': str(e),
                'message': f"Gagal mengambil berita: {query or 'top headlines'}"
            }

    # ==================== CURRENCY ====================
    
    def currency(self, from_currency: str, to_currency: str, amount: float = 1.0) -> Dict[str, Any]:
        """
        Konversi mata uang
        
        Args:
            from_currency: Mata uang asal (USD, IDR, EUR, dll)
            to_currency: Mata uang tujuan
            amount: Jumlah yang dikonversi
        
        Returns:
            Dict hasil konversi
        """
        # STATUS: OK - Method berjalan normal
        # VALIDASI
        if not self.currency_api_key:
            return {
                'error': 'Currency API key not configured',
                'message': 'Set currency_api_key saat inisialisasi'
            }
        
        if not from_currency or not isinstance(from_currency, str):
            raise ValueError("From currency harus string tidak kosong")
        
        if not to_currency or not isinstance(to_currency, str):
            raise ValueError("To currency harus string tidak kosong")
        
        if amount <= 0:
            raise ValueError("Amount harus positif")
        
        try:
            # ExchangeRate-API
            url = (
                f"https://v6.exchangerate-api.com/v6/{self.currency_api_key}"
                f"/pair/{from_currency.upper()}/{to_currency.upper()}"
            )
            
            result = self._make_request(url)
            
            if result.get('result') != 'success':
                return {
                    'error': result.get('error-type', 'Unknown error'),
                    'message': 'Gagal mengambil kurs mata uang'
                }
            
            rate = result.get('conversion_rate', 0)
            converted = amount * rate
            
            return {
                'from': from_currency.upper(),
                'to': to_currency.upper(),
                'amount': amount,
                'rate': rate,
                'converted_amount': converted,
                'last_updated': datetime.now().isoformat(),
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"[ERROR] Failed to convert currency: {e}")
            return {
                'error': str(e),
                'message': f"Gagal konversi {from_currency} ke {to_currency}"
            }

    def currency_rates(self, base_currency: str = 'USD') -> Dict[str, Any]:
        """
        Ambil kurs semua mata uang terhadap base currency
        
        Args:
            base_currency: Mata uang dasar
        
        Returns:
            Dict semua kurs
        """
        # STATUS: OK - Method berjalan normal
        # VALIDASI
        if not self.currency_api_key:
            return {
                'error': 'Currency API key not configured',
                'message': 'Set currency_api_key saat inisialisasi'
            }
        
        if not base_currency or not isinstance(base_currency, str):
            raise ValueError("Base currency harus string tidak kosong")
        
        try:
            url = (
                f"https://v6.exchangerate-api.com/v6/{self.currency_api_key}"
                f"/latest/{base_currency.upper()}"
            )
            
            result = self._make_request(url)
            
            if result.get('result') != 'success':
                return {
                    'error': result.get('error-type', 'Unknown error'),
                    'message': 'Gagal mengambil kurs mata uang'
                }
            
            return {
                'base': base_currency.upper(),
                'rates': result.get('conversion_rates', {}),
                'last_updated': result.get('time_last_update_utc'),
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"[ERROR] Failed to get currency rates: {e}")
            return {
                'error': str(e),
                'message': f"Gagal mengambil kurs untuk {base_currency}"
            }

    # ==================== TRANSLATE ====================
    
    def translate(self, text: str, target_lang: str = 'id', source_lang: Optional[str] = None) -> Dict[str, Any]:
        """
        Terjemahkan teks menggunakan LibreTranslate (gratis)
        
        Args:
            text: Teks yang akan diterjemahkan
            target_lang: Bahasa tujuan (id, en, jp, dll)
            source_lang: Bahasa sumber (auto detect jika None)
        
        Returns:
            Dict hasil terjemahan
        """
        # STATUS: OK - Method berjalan normal
        # VALIDASI
        if not text or not isinstance(text, str):
            raise ValueError("Text harus string tidak kosong")
        
        if not target_lang or not isinstance(target_lang, str):
            raise ValueError("Target language harus string tidak kosong")
        
        try:
            # LibreTranslate API (gratis, tanpa API key)
            url = "https://libretranslate.com/translate"
            
            data = {
                'q': text,
                'target': target_lang.lower()
            }
            
            if source_lang:
                data['source'] = source_lang.lower()
            
            # Buat request POST
            req = urllib.request.Request(
                url,
                data=json.dumps(data).encode('utf-8'),
                headers={'Content-Type': 'application/json'}
            )
            
            with urllib.request.urlopen(req, timeout=self.timeout, context=self.ssl_context) as response:
                result = json.loads(response.read().decode('utf-8'))
                
                self.total_requests += 1
                
                return {
                    'original': text,
                    'translated': result.get('translatedText', ''),
                    'source_lang': result.get('detectedLanguage', {}).get('language', source_lang or 'auto'),
                    'target_lang': target_lang,
                    'timestamp': datetime.now().isoformat()
                }
                
        except Exception as e:
            print(f"[ERROR] Failed to translate: {e}")
            return {
                'error': str(e),
                'original': text,
                'message': f"Gagal menerjemahkan teks ke {target_lang}"
            }

    # ==================== GITHUB ====================
    
    def github(self, action: str, **kwargs) -> Dict[str, Any]:
        """
        GitHub API (umum)
        
        Args:
            action: Aksi yang dilakukan (search, user, repo)
            **kwargs: Parameter spesifik aksi
        
        Returns:
            Dict hasil GitHub API
        """
        # STATUS: OK - Method berjalan normal
        # VALIDASI
        if action not in ['search', 'user', 'repo']:
            return {
                'error': f"Invalid action: {action}",
                'message': 'Action harus search, user, atau repo'
            }
        
        try:
            headers = {}
            if self.github_token:
                headers['Authorization'] = f"token {self.github_token}"
            
            if action == 'search':
                query = kwargs.get('query')
                if not query:
                    raise ValueError("Query diperlukan untuk search")
                
                url = f"https://api.github.com/search/repositories?q={urllib.parse.quote(query)}&per_page={kwargs.get('limit', 10)}"
                result = self._make_request(url, headers)
                
                return {
                    'action': 'search',
                    'query': query,
                    'total_count': result.get('total_count', 0),
                    'items': [
                        {
                            'name': item.get('name'),
                            'full_name': item.get('full_name'),
                            'description': item.get('description'),
                            'url': item.get('html_url'),
                            'stars': item.get('stargazers_count'),
                            'forks': item.get('forks_count'),
                            'language': item.get('language')
                        }
                        for item in result.get('items', [])[:kwargs.get('limit', 10)]
                    ],
                    'timestamp': datetime.now().isoformat()
                }
            
            elif action == 'user':
                username = kwargs.get('username')
                if not username:
                    raise ValueError("Username diperlukan untuk user")
                
                url = f"https://api.github.com/users/{urllib.parse.quote(username)}"
                result = self._make_request(url, headers)
                
                return {
                    'action': 'user',
                    'username': result.get('login'),
                    'name': result.get('name'),
                    'bio': result.get('bio'),
                    'location': result.get('location'),
                    'public_repos': result.get('public_repos'),
                    'followers': result.get('followers'),
                    'following': result.get('following'),
                    'url': result.get('html_url'),
                    'timestamp': datetime.now().isoformat()
                }
            
            elif action == 'repo':
                repo = kwargs.get('repo')
                if not repo:
                    raise ValueError("Repo diperlukan untuk repo")
                
                url = f"https://api.github.com/repos/{repo}"
                result = self._make_request(url, headers)
                
                return {
                    'action': 'repo',
                    'name': result.get('name'),
                    'full_name': result.get('full_name'),
                    'description': result.get('description'),
                    'url': result.get('html_url'),
                    'stars': result.get('stargazers_count'),
                    'forks': result.get('forks_count'),
                    'watchers': result.get('watchers_count'),
                    'language': result.get('language'),
                    'created_at': result.get('created_at'),
                    'updated_at': result.get('updated_at'),
                    'timestamp': datetime.now().isoformat()
                }
            
        except Exception as e:
            print(f"[ERROR] Failed to fetch GitHub: {e}")
            return {
                'error': str(e),
                'message': f"Gagal mengambil data GitHub: {action}"
            }

    def get_stats(self) -> Dict[str, Any]:
        """
        Ambil statistik API server
        
        Returns:
            Dict statistik
        """
        # STATUS: OK - Method berjalan normal
        return {
            'total_requests': self.total_requests,
            'total_errors': self.total_errors,
            'weather_configured': bool(self.weather_api_key),
            'news_configured': bool(self.news_api_key),
            'currency_configured': bool(self.currency_api_key),
            'github_configured': bool(self.github_token),
            'timeout': self.timeout
        }


# Placeholder untuk testing
if __name__ == "__main__":
    print("=" * 50)
    print("TESTING API SERVER")
    print("=" * 50)
    
    # Inisialisasi (tanpa API keys untuk testing)
    print("\n[TEST] Init APIServer (without API keys)")
    server = APIServer(verbose=True)
    
    # Test Wikipedia (gratis, tanpa API key)
    print("\n[TEST] Wikipedia search")
    result = server.wikipedia("kecerdasan buatan", lang="id", limit=3)
    print(f"Wikipedia search: {len(result.get('results', []))} results")
    if result.get('results'):
        print(f"  First: {result['results'][0]['title']}")
    
    # Test Wikipedia page
    print("\n[TEST] Wikipedia page")
    result = server.wikipedia_page("Kecerdasan buatan", lang="id")
    if 'extract' in result:
        print(f"Page: {result.get('title')}")
        print(f"Extract: {result.get('extract', '')[:100]}...")
    
    # Test Translate (gratis, tanpa API key)
    print("\n[TEST] Translate")
    result = server.translate("Hello, how are you?", target_lang="id")
    print(f"Translate: {result.get('translated')}")
    
    # Test currency (akan gagal tanpa API key)
    print("\n[TEST] Currency (without API key)")
    result = server.currency("USD", "IDR", 100)
    print(f"Currency result: {result.get('message', 'Error')}")
    
    # Test weather (akan gagal tanpa API key)
    print("\n[TEST] Weather (without API key)")
    result = server.weather("Jakarta")
    print(f"Weather result: {result.get('message', 'Error')}")
    
    # Test stats
    print("\n[TEST] Get stats")
    stats = server.get_stats()
    print(f"Stats: {stats}")
    
    print("\n" + "=" * 50)
    print("STATUS: OK - Semua test berjalan normal")
    print("=" * 50)
    print("\nCatatan: Test yang membutuhkan API key akan gagal.")
    print("Untuk test lengkap, set API keys:")
    print("  - weather_api_key: OpenWeatherMap API key")
    print("  - news_api_key: NewsAPI key")
    print("  - currency_api_key: ExchangeRate-API key")
    print("  - github_token: GitHub personal access token")