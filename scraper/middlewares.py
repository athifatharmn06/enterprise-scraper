import random

class RandomUserAgentMiddleware:
    """Enterprise middleware to rotate User-Agents and evade basic detection."""
    
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0"
    ]

    def process_request(self, request, spider):
        ua = random.choice(self.USER_AGENTS)
        request.headers['User-Agent'] = ua

class ProxyRotatorMiddleware:
    """Mock Enterprise Proxy Rotator.
    In production, integrates with BrightData or ScraperAPI.
    """
    def process_request(self, request, spider):
        # request.meta['proxy'] = "http://username:password@proxyserver:port"
        pass
