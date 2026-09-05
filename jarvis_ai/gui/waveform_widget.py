"""
BenX Waveform Visualizer - Lightweight, smooth GTK4 DrawingArea voice state indicator.
Visualizes states: idle, listening, recording, thinking, speaking.
"""
import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, GLib
import math
import time


class VoiceWaveformWidget(Gtk.Box):
    """Animated Cairo waveform widget reflecting voice and wake-word status."""

    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.state = "idle"
        self.phase = 0.0
        self.bars = [0.2] * 24

        # Status Label
        self.status_label = Gtk.Label(label="● Voice Ready")
        self.status_label.add_css_class("voice-status-label")
        self.append(self.status_label)

        # Drawing Area
        self.draw_area = Gtk.DrawingArea()
        self.draw_area.set_content_height(38)
        self.draw_area.set_content_width(260)
        self.draw_area.set_draw_func(self._on_draw)
        self.append(self.draw_area)

        # Animation timer (30 fps)
        GLib.timeout_add(33, self._on_tick)

    def set_state(self, state: str):
        """Updates the visualizer state."""
        self.state = state.lower().strip()
        state_labels = {
            "idle": "● Voice: Idle",
            "listening": "● Listening for 'BenX'...",
            "detected": "● Wake word detected!",
            "recording": "🎙️ Recording command...",
            "thinking": "⏳ BenX Thinking...",
            "speaking": "🔊 BenX Speaking...",
        }
        lbl_text = state_labels.get(self.state, f"● {self.state.title()}")
        self.status_label.set_text(lbl_text)

        # CSS class styling
        self.status_label.remove_css_class("voice-listening")
        self.status_label.remove_css_class("voice-recording")
        self.status_label.remove_css_class("voice-thinking")
        self.status_label.remove_css_class("voice-speaking")

        if self.state == "listening":
            self.status_label.add_css_class("voice-listening")
        elif self.state in {"recording", "detected"}:
            self.status_label.add_css_class("voice-recording")
        elif self.state == "thinking":
            self.status_label.add_css_class("voice-thinking")
        elif self.state == "speaking":
            self.status_label.add_css_class("voice-speaking")

        self.draw_area.queue_draw()

    def _on_tick(self):
        self.phase += 0.08
        if self.phase > 2 * math.pi:
            self.phase -= 2 * math.pi
        self.draw_area.queue_draw()
        return True

    def _on_draw(self, area, cr, width, height):
        mid_y = height / 2.0
        cr.set_line_cap(1)  # Round cap

        if self.state == "idle":
            # Subtle steady dotted baseline
            cr.set_source_rgba(0.2, 0.4, 0.45, 0.4)
            cr.set_line_width(2)
            cr.move_to(20, mid_y)
            cr.line_to(width - 20, mid_y)
            cr.stroke()

        elif self.state == "listening":
            # Smooth gentle breathing sine wave (cyan)
            cr.set_source_rgba(0.0, 0.95, 1.0, 0.8)
            cr.set_line_width(2.5)
            cr.move_to(15, mid_y)
            for x in range(15, int(width) - 15, 3):
                y = mid_y + math.sin(x * 0.04 + self.phase) * 6
                cr.line_to(x, y)
            cr.stroke()

        elif self.state in {"recording", "detected"}:
            # Dynamic pulsating bars (neon green & cyan)
            n_bars = 20
            spacing = (width - 40) / (n_bars - 1)
            cr.set_line_width(4)
            for i in range(n_bars):
                x = 20 + i * spacing
                amp = (math.sin(self.phase * 2.5 + i * 0.6) + 1.0) * 0.5
                h = 4 + amp * (height * 0.7)
                # Gradient color transition across bars
                ratio = i / n_bars
                r = 0.0
                g = 0.96 * (1.0 - ratio * 0.2)
                b = 0.6 + ratio * 0.4
                cr.set_source_rgba(r, g, b, 0.9)
                cr.move_to(x, mid_y - h / 2)
                cr.line_to(x, mid_y + h / 2)
                cr.stroke()

        elif self.state == "thinking":
            # Flowing dual-wave (purple & cyan)
            cr.set_line_width(2.5)
            cr.set_source_rgba(0.7, 0.3, 1.0, 0.8)
            cr.move_to(15, mid_y)
            for x in range(15, int(width) - 15, 3):
                y = mid_y + math.sin(x * 0.06 - self.phase * 1.5) * 8
                cr.line_to(x, y)
            cr.stroke()

            cr.set_source_rgba(0.0, 0.9, 1.0, 0.6)
            cr.move_to(15, mid_y)
            for x in range(15, int(width) - 15, 3):
                y = mid_y + math.cos(x * 0.06 + self.phase * 1.2) * 7
                cr.line_to(x, y)
            cr.stroke()

        elif self.state == "speaking":
            # Speaking voice modulation bars
            n_bars = 22
            spacing = (width - 40) / (n_bars - 1)
            cr.set_line_width(3.5)
            cr.set_source_rgba(0.0, 0.85, 0.95, 0.9)
            for i in range(n_bars):
                x = 20 + i * spacing
                dist_from_center = 1.0 - abs(i - n_bars / 2) / (n_bars / 2)
                amp = (math.sin(self.phase * 3 + i * 0.8) + 1) * 0.5 * dist_from_center
                h = 4 + amp * (height * 0.8)
                cr.move_to(x, mid_y - h / 2)
                cr.line_to(x, mid_y + h / 2)
                cr.stroke()
