'''Mobile Automation Engine - AI-powered Android UI automation via ADB.
Mirrors desktop automation.py with ADB/ppadb for taps/swipes/text/OCR/app control.
'''
import json
import time
import base64
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional
try:
    from ppadb.client import Client as _PpadbClient
    PPADB_AVAILABLE = True
except ImportError:
    _PpadbClient = None
    PPADB_AVAILABLE = False
from jarvis_ai.ai_engine import AIEngine
from jarvis_ai.screen_analyzer import ScreenAnalyzer  # Reuse for mobile OCR
from jarvis_ai.config import Config
BENX_DIR = Config.BENX_DIR
from jarvis_ai.utils import log_action

MOBILE_STATE_FILE = BENX_DIR / 'mobile_state.json'

class MobileAutomationEngine:
    def __init__(self, ai_engine: Optional[AIEngine] = None):
        self.ai_engine = ai_engine
        self.client = None
        self.devices = []
        self.device = None
        self.automation_history = []
        self.dry_run = False
        self.paused = False
        if PPADB_AVAILABLE:
            try:
                self.client = _PpadbClient(host='127.0.0.1', port=5037)
                self.devices = self.client.devices()
            except Exception as e:
                self.client = None
                self.devices = []
        self.load_state()

    def connect(self, device_id: str = None) -> str:
        '''Connect to Android device via ADB'''
        try:
            self.devices = self.client.devices()
            if not self.devices:
                return '❌ No ADB devices found. Enable USB debugging: adb devices'
            if device_id:
                self.device = next((d for d in self.devices if device_id in d.serial), None)
            else:
                self.device = self.devices[0] if self.devices else None
            if not self.device:
                return f'❌ Device {device_id} not found. Available: {[d.serial for d in self.devices]}'
            self.save_state()
            return f'✅ Connected to {self.device.serial}'
        except Exception as e:
            return f'❌ ADB connect failed: {str(e)}'

    def list_apps(self) -> List[str]:
        '''List installed packages'''
        if not self.device:
            return ['❌ No device connected']
        result = self.device.shell('pm list packages')
        return [line.replace('package:', '') for line in result.splitlines() if 'package:' in line]

    def list_ui_elements(self, text_query: str = None) -> List[Dict]:
        '''Dump UI hierarchy and search'''
        if not self.device:
            return []
        dump = self.device.shell('uiautomator dump /sdcard/ui.xml')
        if 'error' in dump.lower():
            return []
        # Parse xml (simple regex for demo, improve with lxml)
        import re
        elements = []
        for match in re.finditer(r' text="([^"]*)".*bounds="\\[(\\d+),(\\d+)\\]\\[(\\d+),(\\d+)\\]"', dump):
            text, x1, y1, x2, y2 = match.groups()
            if not text_query or text_query.lower() in text.lower():
                elements.append({
                    'text': text,
                    'bounds': [int(x1), int(y1), int(x2), int(y2)],
                    'center': [int((int(x1)+int(x2))/2), int((int(y1)+int(y2))/2)]
                })
        return elements

    def tap(self, x: int = None, y: int = None, text: str = None) -> str:
        '''Tap by coord or text'''
        if not self.device:
            return '❌ No device'
        if text:
            elements = self.list_ui_elements(text)
            if elements:
                x, y = elements[0]['center']
            else:
                return f'❌ Element "{text}" not found'
        if self.dry_run:
            return f'👀 Dry-run: tap({x},{y})'
        self.device.shell(f'input tap {x} {y}')
        log_action(f'Mobile tap {x},{y}')
        return f'✅ Tapped ({x},{y})'

    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration: int = 500) -> str:
        '''Swipe gesture'''
        if not self.device:
            return '❌ No device'
        if self.dry_run:
            return f'👀 Dry-run: swipe({x1},{y1})→({x2},{y2})'
        self.device.shell(f'input swipe {x1} {y1} {x2} {y2} {duration}')
        log_action(f'Mobile swipe {x1},{y1}→{x2},{y2}')
        return f'✅ Swiped'

    def input_text(self, text: str) -> str:
        '''Type text'''
        if not self.device:
            return '❌ No device'
        if self.dry_run:
            return f'👀 Dry-run: input "{text}"'
        self.device.shell(f'input text "{text}"')
        log_action(f'Mobile input: {text[:20]}...')
        return f'✅ Typed "{text}"'

    def screenshot(self, path: str = None) -> str:
        '''Take screenshot'''
        if not self.device:
            return '❌ No device'
        path = path or str(BENX_DIR / 'mobile_screenshot.png')
        self.device.shell('screencap -p /sdcard/screen.png')
        self.device.pull('/sdcard/screen.png', path)
        return f'✅ Mobile screenshot: {path}'

    def ocr_screen(self) -> str:
        '''Screenshot + OCR via existing analyzer'''
        if self.screenshot():
            analyzer = ScreenAnalyzer()
            text = analyzer.extract_text(str(BENX_DIR / 'mobile_screenshot.png'))
            return text or 'No text detected'

    def launch_app(self, package: str) -> str:
        '''Launch app by package'''
        if not self.device:
            return '❌ No device'
        cmd = f'monkey -p {package} 1'
        self.device.shell(cmd)
        time.sleep(2)
        return f'✅ Launched {package}'

    def understand_automation(self, instruction: str) -> str:
        '''AI plan mobile actions (reuse desktop pattern)'''
        if not self.ai_engine:
            return '[]'
        prompt = f'''Plan mobile automation for: "{instruction}"
Android actions: tap(x,y/text), swipe(x1,y1,x2,y2), input(text), launch(package), screenshot.
Return JSON list: [{{"action": "tap", "text": "send", "description": "tap send"}}]'''
        plan = self.ai_engine.query(prompt)
        try:
            return json.loads(plan)
        except:
            return '[{"action": "error", "params": {"message": "Invalid plan"}}]'

    def preview_automation(self, plan: str) -> str:
        '''Preview steps'''
        try:
            actions = json.loads(plan)
            preview = []
            for a in actions:
                act = a.get('action', '')
                if act == 'tap':
                    preview.append(f'👀 Tap "{a.get("text","?")}" at {a.get("x",?)}')
                # Add more...
            return '\\n'.join(preview)
        except:
            return '❌ Invalid plan'

    def execute_automation(self, plan: str, dry_run: bool = False) -> str:
        '''Execute plan step-by-step'''
        self.dry_run = dry_run
        try:
            actions = json.loads(plan)
            results = []
            for i, action in enumerate(actions):
                result = self._execute_step(action)
                results.append(result)
                if self.paused:
                    break
            self.automation_history.append({'plan': plan, 'results': results})
            return '\\n'.join(results)
        except Exception as e:
            return f'❌ Execution failed: {str(e)}'

    def _execute_step(self, action: Dict) -> str:
        act = action.get('action')
        params = action.get('params', {})
        if act == 'tap':
            return self.tap(**params)
        elif act == 'swipe':
            return self.swipe(**params)
        elif act == 'input':
            return self.input_text(params.get('text', ''))
        elif act == 'launch':
            return self.launch_app(params.get('package', ''))
        elif act == 'screenshot':
            return self.screenshot()
        else:
            return f'❌ Unknown action: {act}'

    def pause(self) -> str:
        self.paused = True
        return '⏸️ Paused'

    def resume(self) -> str:
        self.paused = False
        return '▶️ Resumed'

    def save_state(self):
        state = {'device': self.device.serial if self.device else None, 'history': self.automation_history[-10:]}
        MOBILE_STATE_FILE.write_text(json.dumps(state))

    def load_state(self):
        if MOBILE_STATE_FILE.exists():
            state = json.loads(MOBILE_STATE_FILE.read_text())
            if state.get('device'):
                self.connect(state['device'])

    def automate(self, instruction: str, dry_run: bool = False) -> str:
        '''Full workflow'''
        if not self.device:
            self.connect()
            if not self.device:
                return '❌ Connect device first'
        plan = self.understand_automation(instruction)
        preview = self.preview_automation(plan)
        if dry_run:
            return preview
        return self.execute_automation(plan, dry_run)
