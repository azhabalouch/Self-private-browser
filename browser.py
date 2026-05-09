import sys
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtWebEngineWidgets import *
from PyQt5.QtWebEngineCore import QWebEngineUrlRequestInterceptor
from PyQt5.QtNetwork import QNetworkProxy

# ---------------------------------------------------------
# ENCRYPTED DNS (DoH) CONFIGURATION
# ---------------------------------------------------------
# We must pass these flags to the underlying Chromium engine
# BEFORE we create the QApplication.

# Enable the DNS-over-HTTPS feature
sys.argv.append("--enable-features=dns-over-https")

# Force the browser to use a specific secure DNS server (Cloudflare)
# The URL must be URL-encoded, which is why it looks a bit messy!
cloudflare_doh_url = "https%3A%2F%2Fcloudflare-dns.com%2Fdns-query"
sys.argv.append(
    f"--force-fieldtrial-params=DnsOverHttps.Enabled:server/{cloudflare_doh_url}"
)


class TrackerBlocker(QWebEngineUrlRequestInterceptor):

    def __init__(self):
        super().__init__()
        # A Python 'set' is incredibly fast for checking if something exists in it
        self.blocked_domains = set()
        self.load_blocklist()

    def load_blocklist(self):
        try:
            # Open our text file and load every line into the set
            with open("blocklist.txt", "r") as file:
                for line in file:
                    # Strip out empty spaces and ignore comments
                    domain = line.strip()
                    if domain and not domain.startswith("#"):
                        clean_domain = domain.split()[-1]
                        self.blocked_domains.add(clean_domain)

            print(
                f"✅ Loaded {len(self.blocked_domains)} domains into the blocklist."
            )
        except FileNotFoundError:
            print("⚠️ blocklist.txt not found! Operating without ad blocking.")

    def interceptRequest(self, info):
        # Extract JUST the domain (e.g., 'ads.doubleclick.net' from the full URL)
        url = info.requestUrl()
        host = url.host()

        # We need to check if the specific host OR its parent domain is blocked.
        # If 'doubleclick.net' is blocked, we must also block 'ads.doubleclick.net'
        parts = host.split('.')
        for i in range(len(parts) - 1):
            parent_domain = '.'.join(parts[i:])

            # The ultra-fast lookup: is this domain in our massive set?
            if parent_domain in self.blocked_domains:
                print(f"🛑 AD BLOCKED: {host}")
                info.block(True)
                return


class PrivateBrowser(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("My Private Browser")
        self.resize(1366, 768)

        # ---------------------------------------------------------
        # PRIVACY CONFIGURATION: The core of your private browser
        # ---------------------------------------------------------
        # # Adding proxy to hide your ip
        # proxy = QNetworkProxy(QNetworkProxy.HttpProxy, "your.proxy.address",
        #                       8080)
        # QNetworkProxy.setApplicationProxy(proxy)
        proxy = QNetworkProxy()
        proxy.setType(QNetworkProxy.Socks5Proxy)
        proxy.setHostName("127.0.0.1")
        proxy.setPort(9050)
        QNetworkProxy.setApplicationProxy(proxy)
        self.profile = QWebEngineProfile()

        # Spoof User-Agent
        # We tell websites we are just a standard Windows Chrome browser
        # to blend in with the millions of other users.
        chrome_ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        self.profile.setHttpUserAgent(chrome_ua)

        # Attach the Tracker Blocker
        self.interceptor = TrackerBlocker()
        self.profile.setUrlRequestInterceptor(self.interceptor)

        # Standard Privacy Settings this acts like a permanent Incognito mode.
        self.profile.setPersistentCookiesPolicy(
            QWebEngineProfile.NoPersistentCookies)
        self.profile.setHttpCacheType(QWebEngineProfile.MemoryHttpCache
                                      )  # Only cache in RAM, clears on exit

        # Create a web page using our private profile
        self.webpage = QWebEnginePage(self.profile, self)

        # Initialize the browser view
        self.browser = QWebEngineView()
        self.browser.setPage(self.webpage)

        # Set DuckDuckGo as the default homepage for privacy
        self.browser.setUrl(QUrl('https://duckduckgo.com'))

        # Set the browser as the central widget of the window
        self.setCentralWidget(self.browser)

        # ---------------------------------------------------------
        # USER INTERFACE: Navigation Bar
        # ---------------------------------------------------------
        navbar = QToolBar("Navigation")
        self.addToolBar(navbar)

        # Back Button
        back_btn = QAction('Back', self)
        back_btn.triggered.connect(self.browser.back)
        navbar.addAction(back_btn)

        # Forward Button
        forward_btn = QAction('Forward', self)
        forward_btn.triggered.connect(self.browser.forward)
        navbar.addAction(forward_btn)

        # Reload Button
        reload_btn = QAction('Reload', self)
        reload_btn.triggered.connect(self.browser.reload)
        navbar.addAction(reload_btn)

        # Home Button
        home_btn = QAction('Home', self)
        home_btn.triggered.connect(self.navigate_home)
        navbar.addAction(home_btn)

        # Address Bar
        self.url_bar = QLineEdit()
        self.url_bar.returnPressed.connect(self.navigate_to_url)
        navbar.addWidget(self.url_bar)

        # Update the address bar when the URL changes
        self.browser.urlChanged.connect(self.update_url)

    # ---------------------------------------------------------
    # BROWSER FUNCTIONS
    # ---------------------------------------------------------
    def navigate_home(self):
        self.browser.setUrl(QUrl('https://duckduckgo.com'))

    def navigate_to_url(self):
        url = self.url_bar.text()
        # Automatically add https:// if the user forgets it
        if not url.startswith('http'):
            url = 'https://' + url
        self.browser.setUrl(QUrl(url))

    def update_url(self, q):
        self.url_bar.setText(q.toString())


# ---------------------------------------------------------
# APPLICATION EXECUTION
# ---------------------------------------------------------
app = QApplication(sys.argv)
QApplication.setApplicationName('Private Browser')
window = PrivateBrowser()
window.show()
app.exec_()
