"""Tkinter sliders for head-coupling strength at min vs max zoom (thread-safe)."""

from __future__ import annotations

import sys
import threading


def head_xy_scale_for_zoom(
    zoom_log: float,
    zoom_log_min: float,
    zoom_log_max: float,
    scale_at_min_zoom: float,
    scale_at_max_zoom: float,
) -> float:
    """
    Linear blend of user multipliers over wheel zoom.

    ``zoom_log`` at ``zoom_log_min`` → ``scale_at_min_zoom`` (zoomed *out*).
    ``zoom_log`` at ``zoom_log_max`` → ``scale_at_max_zoom`` (zoomed *in*).
    """
    span = zoom_log_max - zoom_log_min
    if span <= 0:
        return scale_at_min_zoom
    t = (zoom_log - zoom_log_min) / span
    t = max(0.0, min(1.0, t))
    return scale_at_min_zoom * (1.0 - t) + scale_at_max_zoom * t


# Default OpenGL clear colour (matches original portal background).
_DEFAULT_BG_R = 0.08
_DEFAULT_BG_G = 0.08
_DEFAULT_BG_B = 0.10


class HeadSensitivityUI:
    """
    Small always-on-top window: zoom head coupling, smoothing, portal background.
    Thread-safe reads via :meth:`scales`, :meth:`tracking_smoothing_alpha`, :meth:`background_rgb`.
    """

    def __init__(
        self,
        zoom_log_min: float,
        zoom_log_max: float,
        sens_zoomed_out: float = 1.0,
        sens_zoomed_in: float = 1.0,
        tracking_smoothing_alpha: float = 0.25,
        background_rgb: tuple[float, float, float] | None = None,
    ) -> None:
        self._zoom_lo = float(zoom_log_min)
        self._zoom_hi = float(zoom_log_max)
        self._lock = threading.Lock()
        self._sens_out = float(sens_zoomed_out)
        self._sens_in = float(sens_zoomed_in)
        self._track_smooth = float(tracking_smoothing_alpha)
        br, bg, bb = background_rgb or (_DEFAULT_BG_R, _DEFAULT_BG_G, _DEFAULT_BG_B)
        self._bg_r = float(br)
        self._bg_g = float(bg)
        self._bg_b = float(bb)
        self._thread = threading.Thread(target=self._run_tk, daemon=True)
        self._thread.start()

    def scales(self) -> tuple[float, float]:
        """Current (scale at min zoom, scale at max zoom) multipliers."""
        with self._lock:
            return (self._sens_out, self._sens_in)

    def coupling_for_zoom(self, zoom_log: float) -> float:
        so, si = self.scales()
        return head_xy_scale_for_zoom(zoom_log, self._zoom_lo, self._zoom_hi, so, si)

    def tracking_smoothing_alpha(self) -> float:
        """EMA blend for face pose: lower = smoother / slower, higher = snappier."""
        with self._lock:
            return max(0.02, min(0.98, self._track_smooth))

    def background_rgb(self) -> tuple[float, float, float]:
        """Clear colour for the OpenGL window, linear 0–1 per channel."""
        with self._lock:
            return (
                max(0.0, min(1.0, self._bg_r)),
                max(0.0, min(1.0, self._bg_g)),
                max(0.0, min(1.0, self._bg_b)),
            )

    def _run_tk(self) -> None:
        try:
            import tkinter as tk
            from tkinter import ttk
        except Exception as e:
            print("PerspectiveBox: tkinter unavailable, no sensitivity panel:", e, file=sys.stderr)
            return

        root = tk.Tk()
        root.title("PerspectiveBox — head & smoothing")
        root.attributes("-topmost", True)
        root.resizable(False, False)

        frm = ttk.Frame(root, padding=10)
        frm.grid(row=0, column=0, sticky="nsew")

        ttk.Label(
            frm,
            text="Multiplies head X/Y vs wheel zoom.\n"
            "Left = zoomed out; right = zoomed in.",
            wraplength=320,
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 8))

        def make_scale(
            row: int,
            label: str,
            initial: float,
            setter,
        ) -> tk.Scale:
            ttk.Label(frm, text=label).grid(row=row, column=0, sticky="w", pady=4)
            sc = tk.Scale(
                frm,
                from_=0.05,
                to=40,
                resolution=0.05,
                orient=tk.HORIZONTAL,
                length=220,
                showvalue=True,
                command=lambda v: setter(float(v)),
            )
            sc.set(initial)
            sc.grid(row=row, column=1, sticky="ew", padx=(8, 0), pady=4)
            return sc

        def set_out(v: float) -> None:
            with self._lock:
                self._sens_out = v

        def set_in(v: float) -> None:
            with self._lock:
                self._sens_in = v

        make_scale(1, "Zoomed out (min zoom)", self._sens_out, set_out)
        make_scale(2, "Zoomed in (max zoom)", self._sens_in, set_in)

        def set_smooth(v: float) -> None:
            with self._lock:
                self._track_smooth = v

        ttk.Label(frm, text="Face tracking").grid(row=3, column=0, columnspan=2, sticky="w", pady=(10, 2))
        ttk.Label(frm, text="Smoothing (← smoother · snappier →)").grid(row=4, column=0, sticky="w", pady=4)
        sc_sm = tk.Scale(
            frm,
            from_=0.05,
            to=0.95,
            resolution=0.02,
            orient=tk.HORIZONTAL,
            length=220,
            showvalue=True,
            command=lambda v: set_smooth(float(v)),
        )
        sc_sm.set(self._track_smooth)
        sc_sm.grid(row=4, column=1, sticky="ew", padx=(8, 0), pady=4)

        ttk.Label(frm, text="Display").grid(row=5, column=0, columnspan=2, sticky="w", pady=(10, 2))
        disp_row = ttk.Frame(frm)
        disp_row.grid(row=6, column=0, columnspan=2, sticky="w")

        swatch = tk.Label(disp_row, width=5, height=1, relief=tk.SUNKEN, borderwidth=2)

        def refresh_swatch() -> None:
            rr, gg, bb = self.background_rgb()
            ir = max(0, min(255, int(round(rr * 255))))
            ig = max(0, min(255, int(round(gg * 255))))
            ib = max(0, min(255, int(round(bb * 255))))
            swatch.config(bg=f"#{ir:02x}{ig:02x}{ib:02x}")

        def pick_bg() -> None:
            from tkinter import colorchooser

            with self._lock:
                init = (
                    int(self._bg_r * 255),
                    int(self._bg_g * 255),
                    int(self._bg_b * 255),
                )
            c = colorchooser.askcolor(
                initialcolor=init,
                title="Portal background",
                parent=root,
            )
            if c and c[0]:
                r, g, b = c[0]
                with self._lock:
                    self._bg_r = r / 255.0
                    self._bg_g = g / 255.0
                    self._bg_b = b / 255.0
                refresh_swatch()

        ttk.Button(disp_row, text="Background colour…", command=pick_bg).pack(
            side=tk.LEFT, padx=(0, 8)
        )
        swatch.pack(side=tk.LEFT)
        refresh_swatch()

        ttk.Label(
            frm,
            text="Tip: lower “zoomed in” if motion is too strong when fully zoomed.",
            font=("Segoe UI", 8),
            foreground="#444",
        ).grid(row=7, column=0, columnspan=2, sticky="w", pady=(8, 0))

        root.mainloop()


class HeadSensitivityFallback:
    """No UI; same as sliders left at 1.0 / 1.0 (legacy head coupling)."""

    def __init__(self, zoom_log_min: float, zoom_log_max: float) -> None:
        self._zoom_lo = float(zoom_log_min)
        self._zoom_hi = float(zoom_log_max)

    def scales(self) -> tuple[float, float]:
        return (1.0, 1.0)

    def coupling_for_zoom(self, zoom_log: float) -> float:
        return head_xy_scale_for_zoom(
            zoom_log, self._zoom_lo, self._zoom_hi, 1.0, 1.0
        )

    def tracking_smoothing_alpha(self) -> float:
        return 0.25

    def background_rgb(self) -> tuple[float, float, float]:
        return (_DEFAULT_BG_R, _DEFAULT_BG_G, _DEFAULT_BG_B)


def try_open_head_sensitivity_ui(
    zoom_log_min: float,
    zoom_log_max: float,
) -> HeadSensitivityUI | HeadSensitivityFallback:
    try:
        import tkinter as tk  # noqa: F401
    except Exception as e:
        print("PerspectiveBox: tkinter unavailable — head sensitivity panel disabled:", e, file=sys.stderr)
        return HeadSensitivityFallback(zoom_log_min, zoom_log_max)
    try:
        return HeadSensitivityUI(zoom_log_min, zoom_log_max)
    except Exception as e:
        print("PerspectiveBox: could not open sensitivity panel:", e, file=sys.stderr)
        return HeadSensitivityFallback(zoom_log_min, zoom_log_max)
