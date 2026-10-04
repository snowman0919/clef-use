from __future__ import annotations

import io

import AppKit as A
import Foundation as F


class Display:
    def __init__(self):
        self.app = A.NSApplication.sharedApplication()
        self.app.setActivationPolicy_(A.NSApplicationActivationPolicyAccessory)
        self.screen = A.NSScreen.mainScreen().frame()
        self.windows = []
        self.images = [None, None]
        for width, height in ((340, 84), (48, 48)):
            panel = A.NSPanel.alloc().initWithContentRect_styleMask_backing_defer_(
                ((0, 0), (width, height)),
                A.NSWindowStyleMaskNonactivatingPanel,
                A.NSBackingStoreBuffered,
                False,
            )
            panel.setAnimationBehavior_(A.NSWindowAnimationBehaviorNone)
            panel.setHidesOnDeactivate_(False)
            panel.setOpaque_(False)
            panel.setBackgroundColor_(A.NSColor.clearColor())
            panel.setHasShadow_(False)
            panel.setIgnoresMouseEvents_(True)
            panel.setLevel_(A.NSFloatingWindowLevel)
            panel.setCollectionBehavior_(
                A.NSWindowCollectionBehaviorCanJoinAllSpaces
                | A.NSWindowCollectionBehaviorFullScreenAuxiliary
            )
            view = A.NSImageView.alloc().initWithFrame_(((0, 0), (width, height)))
            panel.setContentView_(view)
            self.windows.append((panel, view))

    def _show(self, index, image, x, y):
        window, view = self.windows[index]
        if self.images[index] is not image:
            pool = F.NSAutoreleasePool.alloc().init()
            try:
                buffer = io.BytesIO()
                image.save(buffer, format="PNG")
                pixels = buffer.getvalue()
                data = F.NSData.dataWithBytes_length_(pixels, len(pixels))
                view.setImage_(A.NSImage.alloc().initWithData_(data))
                self.images[index] = image
            finally:
                pool.drain()
        window.setFrameOrigin_((x, y))
        window.setAlphaValue_(1.0)
        window.orderFrontRegardless()
        window.displayIfNeeded()

    def show(self, panel, cursor, point):
        self._show(0, panel, self.screen.origin.x + 18, self.screen.origin.y + 18)
        if point is None:
            self.windows[1][0].orderOut_(None)
        else:
            x, y = point
            self._show(1, cursor, x - 24, self.screen.origin.y + self.screen.size.height - y - 24)

    def hide(self):
        for window, _ in self.windows:
            window.setAlphaValue_(0.0)
            window.orderOut_(None)
        self.app.updateWindows()
        self.pump()

    def pump(self):
        F.NSRunLoop.currentRunLoop().runMode_beforeDate_(
            F.NSDefaultRunLoopMode, F.NSDate.dateWithTimeIntervalSinceNow_(0.003)
        )
        event = self.app.nextEventMatchingMask_untilDate_inMode_dequeue_(
            A.NSEventMaskAny,
            F.NSDate.date(),
            F.NSDefaultRunLoopMode,
            True,
        )
        if event is not None:
            self.app.sendEvent_(event)

    def window_ids(self):
        return [int(window.windowNumber()) for window, _ in self.windows]

    def close(self):
        for window, _ in self.windows:
            window.close()
