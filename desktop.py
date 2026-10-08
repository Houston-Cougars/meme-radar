"""Meme Radar desktop: free public feeds, local SQLite, no credentials."""
import asyncio
import json
import os
import queue
import sqlite3
import sys
import threading
import time
import webbrowser
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote, urlparse
import tkinter as tk
from tkinter import ttk, messagebox

from meme_radar.collectors.rss import RSSCollector
from meme_radar.db import connect, save_posts, save_candidate_snapshots
from meme_radar.analysis.clustering import cluster
from meme_radar.analysis.scoring import score
from meme_radar.analysis.change_detection import annotate_changes

BASE = Path(sys.executable).parent if getattr(sys, 'frozen', False) else Path(__file__).parent
DATA = BASE / 'MemeRadar-data'
BG, PANEL, TEXT, MUTED, ACCENT = '#101820', '#18242e', '#edf4f8', '#91a8b8', '#54dfbb'
DEFAULT_FEEDS = ['https://www.reddit.com/r/memes/.rss', 'https://www.reddit.com/r/dankmemes/.rss',
                 'https://news.google.com/rss/search?q=viral+meme&hl=en-US&gl=US&ceid=US:en']


def validate_settings(feeds, minutes):
    if not feeds:
        raise ValueError('Add at least one public RSS/Atom feed.')
    for feed in feeds:
        parsed = urlparse(feed)
        if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError('Use HTTPS public feed URLs without usernames or passwords.')
    minutes = int(minutes)
    if not 5 <= minutes <= 1440:
        raise ValueError('Choose a collection interval between 5 and 1440 minutes.')
    return {'feeds': feeds, 'minutes': minutes}


def collect_once(settings, directory=DATA):
    directory.mkdir(parents=True, exist_ok=True)
    # Desktop mode cannot activate paid providers or a hosted database.
    os.environ['DATABASE_URL'] = ''
    collector = RSSCollector()
    collector.urls = settings['feeds']
    now = datetime.now(timezone.utc)
    posts = asyncio.run(collector.collect())
    posts = list({(p.platform, p.post_id): p for p in posts}.values())
    con = connect(str(directory / 'history.db'))
    try:
        save_posts(con, posts, now)
        candidates = annotate_changes(con, [score(c) for c in cluster(posts, now)])
        save_candidate_snapshots(con, candidates, now)
    finally:
        con.close()
    payload = {'time': now.isoformat(), 'count': len(posts), 'clusters': len(candidates),
               'feed_results': getattr(collector, 'feed_results', [])}
    (directory / 'last-run.json').write_text(json.dumps(payload, indent=2), encoding='utf-8')
    return payload


class Dashboard:
    def __init__(self, root):
        self.root = root
        DATA.mkdir(parents=True, exist_ok=True)
        self.settings_path = DATA / 'settings.json'
        try:
            self.settings = validate_settings(**json.loads(self.settings_path.read_text(encoding='utf-8')))
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            self.settings = {'feeds': DEFAULT_FEEDS, 'minutes': 60}
        self.events = queue.Queue()
        self.busy, self.running, self.closing = False, True, False
        self.next_run = time.monotonic()
        self.rows = []
        root.title('Meme Radar • Free Local Dashboard')
        root.configure(bg=BG)
        root.geometry('1440x900')
        root.minsize(1000, 650)
        root.attributes('-fullscreen', True)
        root.bind('<Escape>', lambda e: root.attributes('-fullscreen', False))
        root.bind('<F11>', lambda e: root.attributes('-fullscreen', not root.attributes('-fullscreen')))
        root.protocol('WM_DELETE_WINDOW', self.close)
        style = ttk.Style(root)
        style.theme_use('clam')
        style.configure('Treeview', background=PANEL, fieldbackground=PANEL, foreground=TEXT,
                        rowheight=38, borderwidth=0, font=('Segoe UI', 10))
        style.configure('Treeview.Heading', background='#223440', foreground=MUTED, font=('Segoe UI', 10, 'bold'))
        style.map('Treeview', background=[('selected', '#285446')], foreground=[('selected', TEXT)])
        self.build()
        self.load_history()
        try:
            last = json.loads((DATA / 'last-run.json').read_text(encoding='utf-8'))
            self.metrics['fresh'].configure(text=str(last['count']))
            self.metrics['clusters'].configure(text=str(last['clusters']))
            self.metrics['last'].configure(text=datetime.fromisoformat(last['time']).astimezone().strftime('%I:%M %p'))
        except (OSError, ValueError, KeyError):
            pass
        self.root.after(300, self.tick)

    def label(self, parent, text, size=11, color=TEXT, **kwargs):
        return tk.Label(parent, text=text, bg=parent['bg'], fg=color, font=('Segoe UI', size), **kwargs)

    def button(self, parent, text, command, accent=False):
        return tk.Button(parent, text=text, command=command, bg=ACCENT if accent else '#263b48',
                         fg=BG if accent else TEXT, activebackground='#75efd0', relief='flat',
                         padx=16, pady=10, font=('Segoe UI', 10, 'bold'), cursor='hand2')

    def build(self):
        header = tk.Frame(self.root, bg=BG, padx=28, pady=22)
        header.pack(fill='x')
        self.label(header, '◉  MEME RADAR', 25, ACCENT).pack(side='left')
        self.label(header, 'FREE LOCAL / PUBLIC FEEDS', 10, MUTED).pack(side='left', padx=24)
        self.button(header, 'Exit', self.close).pack(side='right')
        self.button(header, 'Full screen · F11', lambda: self.root.attributes('-fullscreen', not self.root.attributes('-fullscreen'))).pack(side='right', padx=8)
        self.button(header, 'Settings', self.open_settings).pack(side='right', padx=8)
        self.button(header, 'Data folder', lambda: os.startfile(str(DATA))).pack(side='right')

        bar = tk.Frame(self.root, bg=BG, padx=28)
        bar.pack(fill='x')
        self.metrics = {}
        for key, title in [('posts', 'SAVED POSTS'), ('fresh', 'LATEST COLLECTION'), ('clusters', 'TEXT CLUSTERS'), ('last', 'LAST UPDATED')]:
            card = tk.Frame(bar, bg=PANEL, padx=22, pady=18)
            card.pack(side='left', fill='x', expand=True, padx=(0, 12))
            self.label(card, title, 10, MUTED).pack(anchor='w')
            value = self.label(card, '—', 24)
            value.pack(anchor='w', pady=(8, 0))
            self.metrics[key] = value

        controls = tk.Frame(self.root, bg=BG, padx=28, pady=20)
        controls.pack(fill='x')
        self.button(controls, 'Collect now', self.scan, True).pack(side='left')
        self.pause_button = self.button(controls, 'Pause', self.toggle)
        self.pause_button.pack(side='left', padx=10)
        self.search = tk.StringVar()
        search = tk.Entry(controls, textvariable=self.search, bg=PANEL, fg=TEXT, insertbackground=TEXT,
                          relief='flat', font=('Segoe UI', 12), width=32)
        search.pack(side='left', padx=(18, 8), ipady=10)
        self.label(controls, 'Filter saved headlines', 10, MUTED).pack(side='left')
        self.search.trace_add('write', lambda *_: self.render_rows())
        self.button(controls, 'Search news', self.search_news).pack(side='right')
        self.status = self.label(self.root, 'Starting collection…', 11, ACCENT, anchor='w', padx=28)
        self.status.pack(fill='x', pady=(0, 12))

        body = tk.Frame(self.root, bg=BG, padx=28)
        body.pack(fill='both', expand=True)
        columns = ('headline', 'author', 'published', 'seen')
        self.table = ttk.Treeview(body, columns=columns, show='headings', selectmode='browse')
        for col, title, width in [('headline', 'HEADLINE / MEME MENTION', 750), ('author', 'AUTHOR', 160), ('published', 'PUBLISHED', 160), ('seen', 'FIRST OBSERVED', 160)]:
            self.table.heading(col, text=title)
            self.table.column(col, width=width, minwidth=100)
        scroll = ttk.Scrollbar(body, orient='vertical', command=self.table.yview)
        self.table.configure(yscrollcommand=scroll.set)
        scroll.pack(side='right', fill='y')
        self.table.pack(fill='both', expand=True)
        self.table.bind('<<TreeviewSelect>>', self.select)
        self.table.bind('<Double-1>', lambda e: self.open_post())
        detail = tk.Frame(self.root, bg=PANEL, padx=28, pady=14)
        detail.pack(fill='x', padx=28, pady=12)
        self.detail = self.label(detail, 'Select a headline to inspect it. Double-click to open the source.', 11, MUTED, anchor='w', wraplength=1100)
        self.detail.pack(side='left', fill='x', expand=True)
        self.button(detail, 'Open source ↗', self.open_post).pack(side='right')
        self.label(self.root, 'RSS mode: no paid APIs • no engagement metrics • collection runs while this app is open • Esc leaves full screen', 10, MUTED).pack(pady=(0, 16))

    def scan(self):
        if self.busy or self.closing:
            return
        self.busy = True
        self.status.configure(text='Collecting public feeds…', fg=ACCENT)
        settings = dict(self.settings)
        def work():
            try:
                self.events.put(('success', collect_once(settings)))
            except Exception as exc:
                self.events.put(('error', f'{type(exc).__name__}: {exc}'))
        threading.Thread(target=work, daemon=True).start()

    def tick(self):
        if self.closing:
            return
        try:
            while True:
                kind, data = self.events.get_nowait()
                self.busy = False
                self.next_run = time.monotonic() + self.settings['minutes'] * 60
                if kind == 'success':
                    self.metrics['fresh'].configure(text=str(data['count']))
                    self.metrics['clusters'].configure(text=str(data['clusters']))
                    self.metrics['last'].configure(text=datetime.fromisoformat(data['time']).astimezone().strftime('%I:%M %p'))
                    feeds = data['feed_results']
                    ok = sum(f['ok'] for f in feeds)
                    self.status.configure(text=f"Collected {data['count']} posts • {ok}/{len(feeds)} feeds available • next run in {self.settings['minutes']} minutes", fg=ACCENT)
                    self.load_history()
                else:
                    self.status.configure(text='Collection failed — ' + data, fg='#ffb577')
                with (DATA / 'activity.log').open('a', encoding='utf-8') as log:
                    log.write(f'{datetime.now().isoformat()} {kind}: {json.dumps(data)}\n')
        except queue.Empty:
            pass
        if self.running and not self.busy and time.monotonic() >= self.next_run:
            self.scan()
        self.root.after(500, self.tick)

    def load_history(self):
        path = DATA / 'history.db'
        if not path.exists():
            return
        with closing(sqlite3.connect(path)) as con:
            self.rows = con.execute('SELECT post_id, text, author_name, created_at, MIN(observed_at), url FROM posts GROUP BY platform,post_id ORDER BY created_at DESC LIMIT 2000').fetchall()
            total = con.execute('SELECT COUNT(*) FROM (SELECT DISTINCT platform,post_id FROM posts)').fetchone()[0]
        self.metrics['posts'].configure(text=f'{total:,}')
        self.render_rows()

    def render_rows(self):
        self.table.delete(*self.table.get_children())
        term = self.search.get().strip().lower()
        self.visible = {}
        for i, row in enumerate(self.rows):
            if term and term not in (row[1] + ' ' + row[2]).lower():
                continue
            key = str(i)
            self.visible[key] = row
            def date(value):
                try:
                    return datetime.fromisoformat(value).astimezone().strftime('%b %d %H:%M')
                except ValueError:
                    return value[:16]
            self.table.insert('', 'end', iid=key, values=(row[1], row[2] or 'News / public feed', date(row[3]), date(row[4])))

    def selected(self):
        selection = self.table.selection()
        return self.visible.get(selection[0]) if selection else None

    def select(self, _=None):
        row = self.selected()
        if row:
            self.detail.configure(text=row[1] + '\n' + row[5], fg=TEXT)

    def open_post(self):
        row = self.selected()
        if row and urlparse(row[5]).scheme in {'https', 'http'}:
            webbrowser.open(row[5])

    def toggle(self):
        self.running = not self.running
        self.pause_button.configure(text='Resume' if not self.running else 'Pause')
        if not self.running:
            self.status.configure(text='Automatic collection paused. A running collection will finish.', fg=MUTED)
        else:
            self.next_run = time.monotonic()

    def search_news(self):
        term = self.search.get().strip()
        if not term:
            messagebox.showinfo('Search news', 'Type a phrase in the search field, then click Search news.')
            return
        if self.busy:
            messagebox.showinfo('Collection running', 'Wait for the current collection to finish, then search news.')
            return
        url = 'https://news.google.com/rss/search?q=' + quote(term + ' meme') + '&hl=en-US&gl=US&ceid=US:en'
        self.settings['feeds'] = list(dict.fromkeys(self.settings['feeds'] + [url]))
        self.settings_path.write_text(json.dumps(self.settings, indent=2), encoding='utf-8')
        self.scan()

    def open_settings(self):
        dialog = tk.Toplevel(self.root)
        dialog.title('Sources & collection')
        dialog.configure(bg=PANEL)
        dialog.geometry('760x500')
        dialog.transient(self.root)
        self.label(dialog, 'Public RSS / Atom feeds (one HTTPS URL per line)', 13).pack(anchor='w', padx=24, pady=20)
        feeds = tk.Text(dialog, bg=BG, fg=TEXT, insertbackground=TEXT, height=10, relief='flat', font=('Segoe UI', 10))
        feeds.pack(fill='both', expand=True, padx=24)
        feeds.insert('1.0', '\n'.join(self.settings['feeds']))
        self.label(dialog, 'Minutes between collections (5–1440)', 11, MUTED).pack(anchor='w', padx=24, pady=(16, 4))
        minutes = tk.Entry(dialog, bg=BG, fg=TEXT, insertbackground=TEXT)
        minutes.pack(anchor='w', padx=24)
        minutes.insert(0, str(self.settings['minutes']))
        def save():
            try:
                self.settings = validate_settings([line.strip() for line in feeds.get('1.0', 'end').splitlines() if line.strip()], minutes.get())
            except ValueError as exc:
                messagebox.showerror('Settings', str(exc), parent=dialog)
                return
            self.settings_path.write_text(json.dumps(self.settings, indent=2), encoding='utf-8')
            self.next_run = time.monotonic()
            dialog.destroy()
        self.button(dialog, 'Save settings', save, True).pack(anchor='e', padx=24, pady=20)

    def close(self):
        self.closing = True
        self.root.destroy()


def main():
    if '--collect-once' in sys.argv:
        result = collect_once({'feeds': DEFAULT_FEEDS, 'minutes': 60})
        (DATA / 'smoke-test.json').write_text(json.dumps(result), encoding='utf-8')
        return
    root = tk.Tk()
    Dashboard(root)
    if '--ui-smoke-test' in sys.argv:
        root.after(3000, root.destroy)
    root.mainloop()


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        DATA.mkdir(parents=True, exist_ok=True)
        (DATA / 'startup-error.txt').write_text(repr(exc), encoding='utf-8')
        raise
