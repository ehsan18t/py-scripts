import os
import sys
import re
from urllib import request
import requests
import argparse
import json
from bs4 import BeautifulSoup
from tqdm import tqdm
from enum import Enum

class Type(Enum):
    DIRECT = 1
    STATIC = 2
    GITHUB = 3
    UNCHANGED = 4
    REDIRECT = 5
    UNCHANGED_BUT_VERSION = 6

class App:
    dl_location: str = ''
    version_pattern = r'([\d\.]+)'
    user_agent = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/113.0',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    }

    def __init__(self, name: str, ext: str, webURL: str, pattern: str, type: int, baseURL: str = '', element: str = 'a'):
        self.name = name
        self.version = ''
        self.ext = ext
        self.webURL = webURL
        self.pattern = pattern
        self.type = type
        self.element = element
        self.link: str = ''
        self.baseURL = baseURL
        self.element = element

    def generate_link(self):
        if self.type == 1:
            self.__get_link()
        elif self.type == 2:
            self.__make_link_with_version()
        elif self.type == 3:
            self.__get_link_from_github()
        elif self.type == 4:
            self.__direct_link()
        elif self.type == 5:
            self.__redirect_link()
        elif self.type == 6:
            self.__direct_link_but_version()
        else:
            print('Type doesn\'t exist!')


    # Generate links for different types
    def hit_request(self, url, stream: bool = None):
        return requests.get(url, headers=App.user_agent, stream=stream)

    def __fetch_soup(self):
        return BeautifulSoup(self.hit_request(self.webURL).content, "html.parser")

    # TYPE: 1
    # If the webURL page has direct link inside the 'a' tag
    def __get_link(self):
        soup = self.__fetch_soup()
        element = soup.find(self.element, href=re.compile(f'{self.pattern}.{self.ext}'))
        if not element:
            print(f'{self.name} with .{self.ext} extension not found!')
        else:
            url = element.get("href")
            self.link = self.baseURL + url
            match = re.search(f'{self.pattern}.{self.ext}', url)
            self.version = match.group(1) if match else 'Unknown'

    # TYPE: 2
    # If the webURL page doesn't contain the direct link
    # However, we know a static link(baseURL) that only differ in version number
    # for different release. So, we find the version from
    # the webURL and replace that inside baseURL.
    def __make_link_with_version(self):
        soup = self.__fetch_soup()
        element = soup.find(self.element, string=re.compile(self.pattern))
        version = re.search(App.version_pattern, element.text).group(1)
        
        if not element or not version:
            print(f'{self.name} with .{self.ext} extension not found!')
        else:
            self.link = self.baseURL.replace('VERSION', version)
            self.version = version

    # TYPE: 3
    # App release is available on github
    # so get the link using github rest api
    def __get_link_from_github(self):
        release = json.loads(self.hit_request(self.webURL).content)
        assets = release['assets']

        for asset in assets:
            if re.search(f'{self.pattern}.{self.ext}', asset['browser_download_url']):
                self.link = asset['browser_download_url']
                self.version = release['tag_name']
                break
        
        if not self.link:
            print(f'{self.name} with .{self.ext} extension not found!')

    # TYPE: 4
    # Direct unchangeable Link
    def __direct_link(self):
        self.link = self.webURL
        self.version = 'Latest'

    # TYPE: 5
    # Not direct link. But will redirect to the direct link
    # so, we are catching that here.
    def __redirect_link(self):
        req = request.Request(self.webURL, headers=App.user_agent)
        self.link = request.build_opener().open(req).geturl()
        # print(self.link)
        if self.link:
            # check if version is fixed
            if self.pattern.startswith('@FIXED '):
                self.version = self.pattern.replace('@FIXED ', '')
            else:
                match = re.search(self.pattern, self.link)
                if match:
                    self.version = match.group(1)
        else:
            print('Failed to generate link')

    # TYPE: 6
    # unchangeable direct link is available but version
    # is on a different page
    def __direct_link_but_version(self):
        self.link = self.baseURL
        soup = self.__fetch_soup()
        element = soup.find(self.element, string=re.compile(self.pattern))
        if not element:
            print(f'version of .{self.name} not found!')
        else:
            match = re.search(self.pattern, element.get_text())
            if match:
                self.version = match.group(1)

    def download(self, path: str = None):
        print(f"\t -> {self}")
        if App.dl_location:
            path = os.path.join(App.dl_location, f'{self.name}_{self.version}.{self.ext}')

        if not path and not App.dl_location:
            path = f'{self.name}_{self.version}.{self.ext}'

        if self.link:
            response = self.hit_request(self.link, stream=True)

            total_size = int(response.headers.get('content-length', 0))
            block_size = 1024 # 1 Kibibyte
            tqdm_bar = tqdm(total=total_size, unit='iB', unit_scale=True)

            with open(path, 'wb') as file:
                for data in response.iter_content(block_size):
                    tqdm_bar.update(len(data))
                    file.write(data)
            tqdm_bar.close()
        else:
            print('Please generate link first!')

    def __str__(self) -> str:
        v = 'v' if 'v' not in self.version else ''
        return f'{self.name} {v}{self.version}.{self.ext}'


def get_app_list():
    return [
            App(
                '7zip',
                'msi',
                'https://www.7-zip.org/download.html',
                r'.*?(\d{1,})-x64',
                Type.DIRECT.value,
                'https://www.7-zip.org/'
            ),
            App(
                'WinRAR',
                'exe',
                'https://www.rarlab.com/download.htm',
                r'.*?winrar.*?64-(.*?)',
                Type.DIRECT.value,
                'https://www.rarlab.com/'
            ),
            App(
                'ImageGlass',
                'msi', 
                'https://api.github.com/repos/d2phap/ImageGlass/releases/latest', 
                r'ImageGlass_Kobe.*?64',
                Type.GITHUB.value
            ),
            App(
                'OBS Studio',
                'exe', 
                'https://api.github.com/repos/obsproject/obs-studio/releases/latest', 
                r'OBS-Studio-(.*?)-Full-Installer-x64',
                Type.GITHUB.value
            ),
            App(
                'SumatraPDF',
                'exe',
                'https://www.sumatrapdfreader.org/download-free-pdf-viewer',
                r'.*?SumatraPDF-(.*?)-64-install',
                Type.DIRECT.value,
                'https://www.sumatrapdfreader.org/'
            ),
            App(
                'AIMP Audio Player',
                'exe',
                'https://www.aimp.ru/?do=download&os=windows',
                r'AIMP v.*?',
                Type.STATIC.value,
                'https://aimp.ru/files/windows/builds/aimp_VERSION_w64.exe',
                'h1'
            ),
            App(
                'Chrome',
                'msi',
                'https://chromeenterprise.google/browser/download/thank-you/?platform=WIN64_MSI&channel=stable&usagestats=0',
                '@FIXED Latest',
                Type.REDIRECT.value
            ),
            App(
                'FireFox',
                'exe',
                'https://download.mozilla.org/?product=firefox-latest&os=win64&lang=en-US',
                r'/([\d.]+[a-z]*\d*)/',
                Type.REDIRECT.value
            ),
            App(
                'Github Desktop',
                'exe',
                'https://central.github.com/deployments/desktop/desktop/latest/win32?format=exe',
                r'/([\d.a-z-]+)/(GitHubDesktopSetup-x64)',
                Type.REDIRECT.value
            ),
            App(
                'VSCode',
                'exe',
                'https://code.visualstudio.com/sha/download?build=stable&os=win32-x64',
                r'-([\d\.]+)',
                Type.REDIRECT.value
            ),
            App(
                'Discord',
                'exe',
                'https://discord.com/api/downloads/distributions/app/installers/latest?channel=stable&platform=win&arch=x86',
                r'/(\d+(\.\d+)+)/',
                Type.REDIRECT.value
            ),
            App(
                'Notepad++',
                'exe',
                'https://api.github.com/repos/notepad-plus-plus/notepad-plus-plus/releases/latest',
                r'npp\.(\d+\.)+\d+\.Installer\.x64',
                Type.GITHUB.value
            ),
            App(
                'SublimeText',
                'exe',
                'https://www.sublimetext.com/download',
                r'Build .*?',
                Type.STATIC.value,
                'https://download.sublimetext.com/sublime_text_build_VERSION_x64_setup.exe',
                'h3'
            ),
            App(
                'QBitTorrent',
                'exe',
                'https://www.qbittorrent.org/download',
                r'Latest: .*?',
                Type.STATIC.value,
                'https://altushost-swe.dl.sourceforge.net/project/qbittorrent/qbittorrent-win32/qbittorrent-VERSION/qbittorrent_VERSION_x64_setup.exe',
            ),
            App(
                'VLC Player',
                'msi',
                'https://www.videolan.org/vlc/download-windows.html',
                r'//get.videolan.org/vlc/(\d+\.\d+\.\d+)/win64/vlc-(\d+\.\d+\.\d+)-win64',
                Type.DIRECT.value,
                'https:'
            ),
            App(
                'Brave Browser',
                'exe',
                'https://api.github.com/repos/brave/brave-browser/releases/latest',
                r'BraveBrowserStandaloneSetup',
                Type.GITHUB.value
            ),
            App(
                'Anydesk',
                'exe',
                'https://anydesk.com/en/downloads/windows',
                r'v([\d.]+)',
                Type.UNCHANGED_BUT_VERSION.value,
                'https://download.anydesk.com/AnyDesk.exe',
                'div'
            ),
            App(
                'Telegram',
                'exe', 
                'https://api.github.com/repos/telegramdesktop/tdesktop/releases/latest', 
                r'/tsetup-x64\.(.*?)',
                Type.GITHUB.value
            ),
            App(
                'Zoom',
                'exe',
                'https://zoom.us/client/latest/ZoomInstaller.exe',
                r'/([\d.]+[a-z]*\d*)/',
                Type.REDIRECT.value
            ),
    ]

def main():
    App.dl_location = dl_location

    app_list = get_app_list()

    for app in app_list:
        app.generate_link()
        # app.download()
        print(app)
        


# Get download location from command line arguments
parser = argparse.ArgumentParser()
parser.add_argument("dl", help="Download location")
args = parser.parse_args()
dl_location = args.dl

# exit if no args given
if not dl_location:
    print("    - Please enter a download location.")
    sys.exit(1)

if __name__ == "__main__":
    main()
