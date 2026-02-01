"""Render HTML to image using WebKit via PyObjC (no external dependencies).

WKWebView must run on the main thread. This module handles dispatching
to the main thread automatically, so callers can invoke from any thread.
"""

import tempfile
import threading
import time

import AppKit
import Foundation
import WebKit
import objc


def html_to_image(html_content: str, width: int = 576, scale: int = 1) -> str:
    """Convert HTML string to a PNG image using WebKit.

    Safe to call from any thread — dispatches to main thread internally.

    Args:
        html_content: Full HTML document string.
        width: Design width in CSS pixels (default 576 for 72mm thermal).
        scale: Render multiplier. The WebKit frame is ``width * scale``
               pixels wide and CSS ``zoom: <scale>`` keeps the layout
               identical, producing a higher-resolution image.

    Returns:
        Path to the generated PNG file.
    """
    output_path = tempfile.NamedTemporaryFile(
        delete=False, suffix=".png"
    ).name

    render_width = width * scale

    if scale > 1:
        zoom_css = f"<style>html{{zoom:{scale};}}</style>"
        if "</head>" in html_content:
            html_content = html_content.replace("</head>", zoom_css + "</head>")
        else:
            html_content = zoom_css + html_content

    if threading.current_thread() is threading.main_thread():
        _render_on_main(html_content, output_path, render_width, scale)
    else:
        error_holder = [None]

        def _work():
            try:
                _render_on_main(html_content, output_path, render_width, scale)
            except Exception as e:
                error_holder[0] = e

        helper = _BlockRunner.alloc().initWithBlock_(_work)
        helper.performSelectorOnMainThread_withObject_waitUntilDone_(
            "execute:", None, True
        )

        if error_holder[0]:
            raise error_holder[0]

    return output_path


class _BlockRunner(AppKit.NSObject):
    """Runs a Python callable on the main thread via performSelector."""

    def initWithBlock_(self, block):
        self = objc.super(_BlockRunner, self).init()
        if self is None:
            return None
        self._block = block
        return self

    def execute_(self, sender):
        if self._block:
            self._block()

    @objc.python_method
    def _unused(self):
        pass


class _NavDelegate(AppKit.NSObject):
    """WKWebView navigation delegate for snapshot capture."""

    def webView_didFinishNavigation_(self, webview, navigation):
        ctx = self._render_ctx
        try:
            _capture_webview(webview, ctx["output_path"], ctx["width"], ctx)
        except Exception as e:
            ctx["error"] = e
            ctx["finished"] = True


def _render_on_main(html: str, output_path: str, width: int, scale: int = 1):
    """Render HTML to PNG. MUST be called on the main thread."""
    done = {"finished": False, "error": None, "output_path": output_path, "width": width, "scale": scale}

    delegate = _NavDelegate.alloc().init()
    delegate._render_ctx = done

    config = WebKit.WKWebViewConfiguration.alloc().init()
    frame = Foundation.NSMakeRect(0, 0, width, 1)
    webview = WebKit.WKWebView.alloc().initWithFrame_configuration_(
        frame, config
    )
    webview.setNavigationDelegate_(delegate)
    webview.loadHTMLString_baseURL_(html, None)

    run_loop = Foundation.NSRunLoop.currentRunLoop()
    deadline = time.time() + 15
    while not done["finished"] and time.time() < deadline:
        run_loop.runMode_beforeDate_(
            Foundation.NSDefaultRunLoopMode,
            Foundation.NSDate.dateWithTimeIntervalSinceNow_(0.05),
        )

    if done["error"]:
        raise done["error"]
    if not done["finished"]:
        raise TimeoutError("WebKit rendering timed out")


def _capture_webview(webview, output_path: str, width: int, done: dict):
    """Evaluate page height and take a snapshot."""

    def on_height(height, error):
        if error:
            done["error"] = RuntimeError(f"JS error: {error}")
            done["finished"] = True
            return

        h = int(float(height)) if height else 800
        # CSS zoom on <html> doesn't affect scrollHeight — multiply manually
        scale = done.get("scale", 1)
        if scale > 1:
            h *= scale
        webview.setFrameSize_(Foundation.NSMakeSize(width, h))

        snap_config = WebKit.WKSnapshotConfiguration.alloc().init()
        snap_config.setSnapshotWidth_(Foundation.NSNumber.numberWithInt_(width))

        def on_snapshot(image, error):
            if error or image is None:
                done["error"] = RuntimeError(
                    f"Snapshot error: {error or 'no image'}"
                )
                done["finished"] = True
                return
            try:
                tiff = image.TIFFRepresentation()
                bitmap = AppKit.NSBitmapImageRep.imageRepWithData_(tiff)
                png_data = bitmap.representationUsingType_properties_(
                    AppKit.NSBitmapImageFileTypePNG, {}
                )
                png_data.writeToFile_atomically_(output_path, True)
            except Exception as e:
                done["error"] = e
            finally:
                done["finished"] = True

        webview.takeSnapshotWithConfiguration_completionHandler_(
            snap_config, on_snapshot
        )

    webview.evaluateJavaScript_completionHandler_(
        "document.body.scrollHeight", on_height
    )
