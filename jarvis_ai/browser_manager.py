"""
BrowserManager - Persistent browser state with tab/workspace awareness for Jarvis AI
Singleton manager tracks Chromium contexts/pages per Hyprland workspace.
Smart open: check existing tabs/windows → switch/focus, else open new.
Persistent via memory_engine. Integrates workspace_monitor for window control.
"""
import logging
import json
import asyncio
import os
from typing import Dict, Optional, List, Tuple
from pathlib import Path
import weakref

from playwright.async_api import async_playwright, BrowserContext, Page

from jarvis_ai.workspace_monitor import WorkspaceMonitor
from jarvis_ai.memory_engine import MemoryEngine
from jarvis_ai.config import Config

logger = logging.getLogger(__name__)

class BrowserManager:
    _instance = None
    _lock = asyncio.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if hasattr(self, '_initialized'):
            return
        self._initialized = True
        
        self.memory = MemoryEngine(Config.MEMORY_FILE)
        self.contexts: Dict[int, BrowserContext] = {}  # ws_id → context
        self.pages: Dict[int, List[Tuple[Page, str]]] = {}  # ws_id → [(page, url)]
        self.chrome_windows: Dict[int, Dict] = {}  # ws_id → chrome client info
        self._playwright = None
        self._browser = None
        
        # Load persistent state
        self._load_state()
        
        # Weakref to avoid cycles
        self._weak_self = weakref.ref(self)
    
    async def __aenter__(self):
        await self.ensure_browser()
        return self
    
    async def __aexit__(self, *args):
        await self.close()
    
    async def ensure_browser(self):
        """Ensure persistent browser ready (headless=False for tabs)."""
        if self._playwright is None:
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(
                headless=False,  # Visible tabs
                args=['--no-first-run', '--disable-infobars']
            )
        return self._browser
    
    def get_workspace_id(self) -> int:
        """Get current active workspace."""
        return WorkspaceMonitor.get_active_workspace_id()
    
    async def get_or_open_tab(self, url: str, workspace_id: Optional[int] = None) -> str:
        """
        Smart open: 
        1. Check memory/pages for existing tab → activate it.
        2. Check workspace Chrome windows → focus/switch.
        3. Else create new tab in context for WS.
        Returns: '✅ Switched to existing tab' or '✅ Opened new tab'.
        """
        if not url.startswith(('http', 'https')):
            url = 'https://' + url.lstrip('/')
        
        ws_id = workspace_id or self.get_workspace_id()
        
        # 1. Check existing pages/tabs
        if ws_id in self.pages:
            for page, page_url in self.pages[ws_id]:
                if url in page_url or page_url in url:
                    await page.bring_to_front()
                    self._save_state()
                    return f"✅ Switched to existing tab: {page_url} (workspace {ws_id})"
        
        # 2. Check if Chrome running in target WS → focus/switch
        chrome_info = await self._find_chrome_window(ws_id)
        if chrome_info:
            success = WorkspaceMonitor.focus_window_by_title(chrome_info['title'])
            if ws_id != self.get_workspace_id():
                WorkspaceMonitor.switch_workspace(ws_id)
            if '✅' in success:
                # Create/attach new tab (new context if none)
                context = await self._get_context(ws_id)
                page = await context.new_page()
                await page.goto(url, wait_until='networkidle')
                self.pages.setdefault(ws_id, []).append((page, url))
                self._save_state()
                return f"✅ Opened new tab in existing Chrome (workspace {ws_id}): {url}"
        
        # 3. Full new: create context/page
        context = await self._get_context(ws_id)
        page = await context.new_page()
        await page.goto(url, wait_until='networkidle')
        self.pages.setdefault(ws_id, []).append((page, url))
        self._save_state()
        return f"✅ Opened new tab: {url} (workspace {ws_id})"
    
    async def _get_context(self, ws_id: int) -> BrowserContext:
        """Get/create persistent context for workspace."""
        if ws_id not in self.contexts:
            self.contexts[ws_id] = await self._browser.new_context(
                viewport={'width': 1920, 'height': 1080}
            )
        return self.contexts[ws_id]
    
    async def list_tabs(self, workspace_id: Optional[int] = None) -> str:
        """List open tabs per workspace."""
        ws_id = workspace_id or self.get_workspace_id()
        tabs = self.pages.get(ws_id, [])
        if not tabs:
            return f"📂 No tabs tracked in workspace {ws_id}"
        
        lines = [f"📂 Workspace {ws_id} tabs ({len(tabs)}):"]
        for i, (page, url) in enumerate(tabs, 1):
            title = await page.title()
            lines.append(f"  {i}. {title[:50]} → {url[:60]}")
        return "\n".join(lines)
    
    async def switch_to_tab(self, query: str, workspace_id: Optional[int] = None) -> str:
        """Switch to tab matching query (url/title)."""
        ws_id = workspace_id or self.get_workspace_id()
        tabs = self.pages.get(ws_id, [])
        for page, url in tabs:
            title = await page.title()
            if query.lower() in title.lower() or query.lower() in url.lower():
                await page.bring_to_front()
                self._save_state()
                return f"✅ Switched to tab: {title[:50]} ({url[:60]})"
        return f"❌ No tab matching '{query}' in workspace {ws_id}"
    
    async def _find_chrome_window(self, ws_id: int) -> Optional[Dict]:
        """Find Chrome window in target WS via workspace_monitor."""
        clients = WorkspaceMonitor.get_all_clients()
        for client in clients:
            if client.get('workspace', {}).get('id') == ws_id:
                cls = client.get('class', '').lower()
                if 'chrome' in cls or 'chromium' in cls:
                    self.chrome_windows[ws_id] = client
                    return client
        return None
    
    def _load_state(self):
        """Restore from memory_engine."""
        state = self.memory.get_fact('browser_state') or '{}'
        try:
            data = json.loads(state)
            # Load metadata only - pages/contexts recreated on demand
            self.pages_meta = data.get('pages', {})  # ws_id → [(None, url)]
            logger.info(f"🔄 Loaded browser metadata: {len(self.pages_meta)} workspaces")
        except Exception:
            self.pages_meta = {}

    async def _find_chrome_window(self, ws_id: int) -> Optional[Dict]:
        """Find Chrome/Chromium window in target WS."""
        clients = WorkspaceMonitor.get_all_clients()
        for client in clients:
            if client.get('workspace', {}).get('id') == ws_id:
                cls = client.get('class', '').lower()
                if any(x in cls for x in ['chrome', 'chromium', 'google-chrome']):
                    self.chrome_windows[ws_id] = client
                    return client
        return None
    
    def _save_state(self):
        """Save tab metadata to memory (pages can't be serialized)."""
        state = {
            'pages': {ws: [(None, url) for _, url in tabs] for ws, tabs in self.pages.items()}
        }
        self.memory.learn_fact('browser_state', json.dumps(state))
    
    async def close(self):
        """Cleanup."""
        for context in self.contexts.values():
            await context.close()
        self.contexts.clear()
        self.pages.clear()
        self.chrome_windows.clear()
        if self._playwright:
            await self._playwright.stop()
        self._save_state()
        logger.info("🔒 BrowserManager closed")

# Global convenience access
browser_manager = BrowserManager()

