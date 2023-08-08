import os
import sys
import re
import tkinter as tk
from tkinter import ttk
from ttkbootstrap import Style
import threading
import requests
from urllib import request
import json
from bs4 import BeautifulSoup
import tkinter.messagebox as messagebox
from enum import Enum


class Type(Enum):
    DIRECT = 1
    STATIC = 2
    GITHUB = 3
    UNCHANGED = 4
    REDIRECT = 5
    UNCHANGED_BUT_VERSION = 6
    DIRECT_THEN_REDIRECT = 7


class App:
    dl_location: str = f'{os.getcwd()}/Apps' 
    version_pattern = r'([\d\.]+)'
    user_agent = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/113.0',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    }

    def __init__(self, name: str, ext: str, webURL: str, pattern: str, type: int, baseURL: str = '', element: str = 'a', checked=False):
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
        self.checked = checked

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
        elif self.type == 7:
            self.__get_link_then_redirect()
        else:
            print('Type doesn\'t exist!')

    def __str__(self) -> str:
        return f'{self.name} {self.version}.{self.ext}'


    # Generate links for different types
    def hit_request(self, url, stream: bool = None):
        return requests.get(url, headers=App.user_agent, stream=stream)

    def __fetch_soup(self):
        return BeautifulSoup(self.hit_request(self.webURL).content, "html.parser")

    def __get_link_base(self):
        soup = self.__fetch_soup()
        element = soup.find(self.element, href=re.compile(f'{self.pattern}.{self.ext}'))
        if not element:
            print(f'{self.name} with .{self.ext} extension not found!')
        else:
            return self.baseURL + element.get("href")
        return ''

    # TYPE: 1
    # If the webURL page has direct link inside the 'a' tag
    def __get_link(self):
        self.link = self.__get_link_base()
        if self.link:
            match = re.search(f'{self.pattern}.{self.ext}', self.link)
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
        # req = request.Request(self.webURL, headers=App.user_agent)
        # self.link = request.build_opener().open(req).geturl()
        req = requests.get(self.webURL, allow_redirects=False)
        self.link = req.headers['Location']
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

    # TYPE: 7
    # This is basically a combination of type 1 and 5
    # Where first we've to find link with type-1 and
    # then redirect to the direct link with type-5 for downloading
    def __get_link_then_redirect(self):
        url = self.__get_link_base()
        req = requests.get(url, allow_redirects=False)
        self.link = req.headers['Location']
        # req = request.Request(url, headers=App.user_agent)
        # self.link = request.build_opener().open(req).geturl()


class AppDownloaderGUI:
    def __init__(self, root):
        self.root = root
        self.version = '1.0.0'
        self.root.title(f"App Downloader v{self.version}")
        self.root.resizable(False, False)
        self.style = Style(theme="flatly")
        self.cancel_downloads = False
        self.download_thread = None
        self.downloads_complete = False
        self.apps = get_app_list()
        self.create_widgets()

    def create_widgets(self):
        frame = ttk.Frame(self.root)
        frame.pack(padx=20, pady=20)
        canvas = tk.Canvas(frame)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
        scrollbar.pack(side="right", fill="y")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"))
        app_frame = ttk.Frame(canvas)
        canvas.create_window((0, 0), window=app_frame, anchor="nw")
        self.app_vars = []
        for i, app in enumerate(self.apps):
            var = tk.BooleanVar(value=app.checked)
            checkbox = ttk.Checkbutton(app_frame, text=app.name, variable=var, style="TCheckbutton")
            checkbox.pack(anchor="w", padx=10, pady=5)
            app.var = var
            self.app_vars.append(var)

        button_frame = ttk.Frame(self.root)
        button_frame.pack(pady=10)

        self.progress_label = ttk.Label(button_frame, text="")
        self.progress_label.pack(side="top", padx=5, pady=5)

        self.select_all_button = ttk.Button(button_frame, text="Select All", command=self.toggle_select_all, takefocus=False)
        self.select_all_button.pack(side="left", padx=5)

        self.download_button = ttk.Button(button_frame, text="Download Selected", command=self.download_selected_apps, takefocus=False)
        self.download_button.pack(side="left", padx=5)

        self.cancel_button = ttk.Button(button_frame, text="Cancel", command=self.cancel_download)


        self.root.protocol("WM_DELETE_WINDOW", self.close_app)  # Handle window close event

    def toggle_select_all(self):
        selected = all(var.get() for var in self.app_vars)
        for var in self.app_vars:
            var.set(not selected)
        if selected:
            self.select_all_button.configure(text="Select All")
        else:
            self.select_all_button.configure(text="Deselect All")

    def download_selected_apps(self):
        selected_apps = [app for app, var in zip(self.apps, self.app_vars) if var.get()]
        if not selected_apps:
            messagebox.showwarning("Download", "Please select at least one app.")
            return

        if self.download_thread and self.download_thread.is_alive():
            messagebox.showwarning("Download", "Another download is already in progress.")
            return

        self.select_all_button.configure(state="disabled")
        self.download_button.configure(state="disabled")

        self.progress_label.configure(text="Downloading...")
        self.progress_label.update()

        self.cancel_downloads = False
        self.downloads_complete = False
        self.show_cancel_button()

        self.download_thread = threading.Thread(target=self.download_apps, args=(selected_apps,))
        self.download_thread.start()

    def create_dir(self):
        if App.dl_location:
            path = os.path.join(App.dl_location)
            if not os.path.exists(path):
                os.makedirs(path)

    def download_apps(self, apps):
        for app in apps:
            if self.cancel_downloads:
                break

            try:
                app.generate_link()
                print(app.link)
                self.create_dir() # create if path not exist
                path = os.path.join(App.dl_location, f'{app.name}_{app.version}.{app.ext}')
                response = app.hit_request(app.link, stream=True)
                total_size = int(response.headers.get("content-length", 0))
                if total_size == 0:
                    total_size = 1
                block_size = 1024  # 1 Kibibyte

                with open(path, "wb") as file:
                    downloaded_size = 0
                    for data in response.iter_content(block_size):
                        if self.cancel_downloads:
                            break
                        if not threading.current_thread().is_alive():  # Check if the download process should be stopped
                            break

                        file.write(data)
                        downloaded_size += len(data)
                        progress = int((downloaded_size / total_size) * 100)

                        self.root.after(10, self.update_progress_label, app, progress)  # Schedule GUI update in the main thread

                    if threading.current_thread().is_alive():  # Check if the download process was not stopped
                        if self.cancel_downloads:
                            messagebox.showinfo("Download", f"{app} download canceled.")

            except Exception as e:
                if threading.current_thread().is_alive():  # Check if the download process was not stopped
                    messagebox.showerror("Download Error", f"An error occurred while downloading {app.name}: {str(e)}")

        self.downloads_complete = True
        messagebox.showinfo("Download", f"Downloaded Selected Apps Successfully.")
        self.reset_ui()

    def update_progress_label(self, app, value):
        self.progress_label.configure(text=f"Downloading {app}: {value}%")
        self.progress_label.update_idletasks()


    def reset_ui(self):
        self.select_all_button.configure(state="normal")
        self.download_button.configure(state="normal")
        self.hide_cancel_button()

        # Show or hide the cancel button based on download status
        if self.downloads_complete:
            self.hide_cancel_button()
        else:
            self.show_cancel_button()

        self.progress_label.configure(text="")

    def show_cancel_button(self):
        self.cancel_button.pack(side="left", padx=5)

    def hide_cancel_button(self):
        self.cancel_button.pack_forget()

    def _interrupt_download(self):
        if self.download_thread and self.download_thread.is_alive():
            if messagebox.askyesno("Cancel Downloads", "Are you sure you want to cancel the downloads?"):
                self.cancel_downloads = True  # Set the flag to cancel downloads
                self.download_thread.join(Timeout=1) # Do not fix the typo, it is intentional

    def close_app(self):
        self._interrupt_download()
        self.root.destroy()

    def cancel_download(self):
        self._interrupt_download()
        self.reset_ui()





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
                'https://chromeenterprise.google/browser/download/thank-you/?platform=WIN64_MSI&channel=stable&usagestats=1',
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
                'msi',
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
                Type.DIRECT_THEN_REDIRECT.value,
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



root = tk.Tk()
app = AppDownloaderGUI(root)
root.mainloop()


