import os
import sys
import re
import requests
import argparse
import json
import shutil
import wget
from bs4 import BeautifulSoup


# Get download location from command line arguments
parser = argparse.ArgumentParser()
parser.add_argument("dl", help="Download location")
args = parser.parse_args()
dl_location = args.dl

# exit if no args given
if not dl_location:
    print("    - Please enter a download location.")
    sys.exit(1)


# Define download links and regex patterns
download_dict = {
    # "7zip": {
    #     "url": "https://www.7-zip.org/download.html",
    #     "pattern": r".*?\d{1,}-x64.msi",
    #     "pre": "https://www.7-zip.org/",
    #     "type": 1
    # },
    # "winrar": {
    #     "url": "https://www.rarlab.com/download.htm",
    #     "pattern": r".*?winrar.*?64.*?exe",
    #     "pre": "https://www.rarlab.com/",
    #     "type": 1
    # },
    # "imageglass": {
    #     "url": "https://api.github.com/repos/d2phap/ImageGlass/releases/latest",
    #     "pattern": r"ImageGlass_Kobe.*?64.msi",
    #     "pre": "",
    #     "type": 2
    # },
    # "sumatrapdf": {
    #     "url": "https://www.sumatrapdfreader.org/download-free-pdf-viewer.html",
    #     "pattern": r".*?SumatraPDF-.*?-install.exe",
    #     "pre": "https://www.sumatrapdfreader.org/",
    #     "type": 1
    # },
    # "aimp": {
    #     "url": "https://www.aimp.ru/?do=download&os=windows",
    #     "pattern": r"AIMP v.*?",
    #     "pre": "https://aimp.ru/files/windows/builds/aimp_VERSION_w64.exe",
    #     "type": 3,
    #     "element": "h1",
    #     "versionPattern": r'([\d\.]+)'
    # },
    # "chrome": {
    #     "url": "https://dl.google.com/tag/s/appguid%3D%7B8A69D345-D564-463C-AFF1-A69D9E530F96%7D%26iid%3D%7B0AEE820D-AF8E-419F-7C36-815C47D7D2C6%7D%26lang%3Den%26browser%3D3%26usagestats%3D0%26appname%3DGoogle%2520Chrome%26needsadmin%3Dprefers%26ap%3Dx64-stable-statsdef_1%26installdataindex%3Dempty/chrome/install/ChromeStandaloneSetup64.exe",
    #     "pattern": r"",
    #     "pre": "",
    #     "type": 4,
    #     "name": "chrome_installer.exe"
    # },
    # "firefox": {
    #     "url": "https://download.mozilla.org/?product=firefox-latest&os=win64&lang=en-US",
    #     "pattern": r"",
    #     "pre": "",
    #     "type": 4,
    #     "name": "firefox_installer.exe"
    # },
    # "npp": {
    #     "url": "https://api.github.com/repos/notepad-plus-plus/notepad-plus-plus/releases/latest",
    #     "pattern": r'npp\.(\d+\.)+\d+\.Installer\.x64\.exe',
    #     "pre": "",
    #     "type": 2
    # },
    # "sublimetext": {
    #     "url": "https://www.sublimetext.com/download",
    #     "pattern": r"Build .*?",
    #     "pre": "https://download.sublimetext.com/sublime_text_build_VERSION_x64_setup.exe",
    #     "type": 3,
    #     "element": "h3",
    #     "versionPattern": r'([\d\.]+)'
    # },
    # "qbit": {
    #     "url": "https://www.qbittorrent.org/download",
    #     "pattern": r"Latest: .*?",
    #     "pre": "https://altushost-swe.dl.sourceforge.net/project/qbittorrent/qbittorrent-win32/qbittorrent-VERSION/qbittorrent_VERSION_x64_setup.exe",
    #     "type": 3,
    #     "element": "a",
    #     "versionPattern": r'([\d\.]+)'
    # },
    # "vlc": {
    #     "url": "https://www.videolan.org/vlc/download-windows.html",
    #     "pattern": r"//get.videolan.org/vlc/\d+\.\d+\.\d+/win64/vlc-\d+\.\d+\.\d+-win64.msi",
    #     "pre": "https:",
    #     "type": 1
    # },
    "brave": {
        "url": "https://api.github.com/repos/brave/brave-browser/releases/latest",
        "pattern": r'BraveBrowserStandaloneSetup.exe',
        "pre": "",
        "type": 2,
        "name": "Brave VERSION.exe"
    },
}


def fetch_soup(url):
    # Download webpage
    return BeautifulSoup(requests.get(url).content, "html.parser")


def make_link_with_version(value):
    url = value["url"]
    pattern = value["pattern"]

    soup = fetch_soup(url)

    # Find download link using regex
    element = soup.find(value['element'], string=re.compile(pattern))
    version = re.search(value['versionPattern'], element.text).group(1)
    value['pre'] = value['pre'].replace('VERSION', version)

    return ""


def get_link(value):
    url = value["url"]
    pattern = value["pattern"]

    soup = fetch_soup(url)

    # Find download link using regex
    return soup.find("a", href=re.compile(pattern)).get("href")


def move_file(filename, location):
    shutil.move(filename, location)


def get_link_from_github(value):
    url = value["url"]
    pattern = value["pattern"]
    selected_asset = None

    release = json.loads(requests.get(url).content)
    assets = release['assets']
    asset_link = ""

    for asset in assets:
        if re.search(pattern, asset['name']):
            selected_asset = asset
            asset_link = asset['browser_download_url']
            break

    # add version code incase its missing 
    name = value.get('name', None)
    if selected_asset and name is not None:
        value['name'] = name.replace('VERSION', release['tag_name'])

    return asset_link


def custom_bar(current, total, width=20):
    return wget.bar_adaptive(round(current/1024/1024, 2), round(total/1024/1024, 2)) + ' MB'

def download(url, path):
    print(f"\t -> {path}")
    wget.download(url=url, out=path, bar=custom_bar)
    print('\n')


# Download and save files
for key, value in download_dict.items():
    # Direct dl link is available in download page
    if value['type'] == 1:
        link = get_link(value)
    # Download from gtihub using rest api 
    elif value['type'] == 2:
        link = get_link_from_github(value)
    # Download link direct not available, extract version
    # then replace the version within the static download link
    elif value['type'] == 3:
        link = make_link_with_version(value)
    # Direct Download Link
    elif value['type'] == 4:
        link = value['url']

    pre = value["pre"]

    # If link is found, download file
    if link is not None:
        name = value.get('name', None)
        download_url = pre + link
        file_name = download_url.split("/")[-1] if not name else value['name']
        download(download_url, file_name)
        move_file(file_name, os.path.join(dl_location, file_name))
    else:
        print(f"\t - {key}: Could not find a download link.")
