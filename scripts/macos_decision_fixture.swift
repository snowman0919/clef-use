// Usage: swift -swift-version 5 scripts/macos_decision_fixture.swift <fresh-output-directory>
// Native owned-view rendering only: not an OS screenshot, live OS input, or task E2E.
// The only transitions are NSButton.performClick -> native AppKit target/action callbacks.
#if os(macOS)
import AppKit
import CryptoKit
import Darwin
import Foundation

private let timeoutSeconds = 45

private func fail(_ message: String) -> Never {
    fputs("macos_decision_fixture: \(message)\n", stderr)
    exit(EXIT_FAILURE)
}

private struct Rect: Codable, Equatable {
    let x: Double
    let y: Double
    let width: Double
    let height: Double

    init(_ rect: NSRect, scaleX: Double = 1, scaleY: Double = 1) {
        x = Double(rect.minX) * scaleX
        y = Double(rect.minY) * scaleY
        width = Double(rect.width) * scaleX
        height = Double(rect.height) * scaleY
    }
}

private struct WidgetRectangle: Codable, Equatable {
    let points: Rect
    let pixels: Rect
    let hidden: Bool
}

private struct Readback: Codable, Equatable {
    let stage: String
    let heading: String
    let instruction: String
    let button_title: String
    let button_hidden: Bool
    let button_enabled: Bool
    let final_label: String
    let final_label_hidden: Bool
    let widget_rectangles: [String: WidgetRectangle]
}

private struct StageRecord: Codable, Equatable {
    let index: Int
    let stage: String
    let filename: String
    let sha256: String
    let pixel_width: Int
    let pixel_height: Int
    let view_bounds_points: Rect
    let pixels_per_point_x: Double
    let pixels_per_point_y: Double
    let trigger: String
    let native_action_callback_count: Int
    let readback: Readback
}

private struct Manifest: Codable, Equatable {
    let schema_version: Int
    let fixture_kind: String
    let platform: String
    let os_name: String
    let os_version: String
    let os_version_components: [String: Int]
    let architecture: String
    let process_architecture: String
    let darwin_kernel_release: String
    let capture_method: String
    let capture_scope: String
    let transition_method: String
    let readback_method: String
    let native_input: Bool
    let os_screenshot: Bool
    let desktop_e2e: Bool
    let task_e2e: Bool
    let model_inference: Bool
    let appearance: String
    let window_backing_scale_factor: Double
    let coordinate_convention: [String: String]
    let collector_timeout_seconds: Int
    let stage_count: Int
    let stages: [StageRecord]
}

@MainActor
private final class OwnedFixtureView: NSView {
    override var isFlipped: Bool { true }
    override var isOpaque: Bool { true }

    override func draw(_ dirtyRect: NSRect) {
        NSColor.windowBackgroundColor.setFill()
        NSBezierPath.fill(dirtyRect)
    }
}

@MainActor
private final class Collector: NSObject, NSApplicationDelegate {
    private let output: URL
    private var window: NSWindow?
    private var button: NSButton?
    private var stageLabel: NSTextField?
    private var instruction: NSTextField?
    private var finalLabel: NSTextField?
    private var callbackCount = 0
    private var records: [StageRecord] = []

    init(output: URL) {
        self.output = output
        super.init()
    }

    func applicationDidFinishLaunching(_ notification: Notification) {
        guard !NSScreen.screens.isEmpty else {
            fail("No AppKit screen on this Darwin runner; no fixtures synthesized")
        }
        guard let appearance = NSAppearance(named: .aqua) else {
            fail("AppKit could not create the owned view appearance")
        }
        let root = OwnedFixtureView(frame: NSRect(x: 0, y: 0, width: 640, height: 360))
        root.appearance = appearance
        let ownedWindow = NSWindow(
            contentRect: root.frame, styleMask: [.titled], backing: .buffered, defer: false
        )
        ownedWindow.title = "Native owned-view decision fixture"
        ownedWindow.isReleasedWhenClosed = false
        ownedWindow.appearance = appearance
        ownedWindow.contentView = root
        window = ownedWindow

        func label(_ id: String, _ text: String, _ frame: NSRect, _ font: NSFont) -> NSTextField {
            let widget = NSTextField(labelWithString: text)
            widget.identifier = NSUserInterfaceItemIdentifier(id)
            widget.frame = frame
            widget.font = font
            root.addSubview(widget)
            return widget
        }
        _ = label(
            "heading", "Local test workspace", NSRect(x: 32, y: 32, width: 576, height: 36),
            .boldSystemFont(ofSize: 26)
        )
        stageLabel = label(
            "stage_label", "Continue", NSRect(x: 32, y: 92, width: 576, height: 30),
            .systemFont(ofSize: 20)
        )
        instruction = label(
            "instruction", "Continue to the confirmation step.",
            NSRect(x: 32, y: 142, width: 576, height: 30), .systemFont(ofSize: 16)
        )
        finalLabel = label(
            "final_label", "", NSRect(x: 32, y: 274, width: 576, height: 34),
            .boldSystemFont(ofSize: 22)
        )
        finalLabel?.isHidden = true
        let nativeButton = NSButton(title: "Continue", target: self, action: #selector(advance(_:)))
        nativeButton.identifier = NSUserInterfaceItemIdentifier("button")
        nativeButton.frame = NSRect(x: 32, y: 208, width: 160, height: 40)
        nativeButton.bezelStyle = .rounded
        nativeButton.setButtonType(.momentaryPushIn)
        nativeButton.font = .systemFont(ofSize: 16)
        root.addSubview(nativeButton)
        button = nativeButton
        ownedWindow.center()
        ownedWindow.orderFront(nil)
        scheduleCapture()
    }

    @objc private func advance(_ sender: NSButton) {
        guard let button = button, sender === button, button.isEnabled, !button.isHidden else {
            fail("Unexpected native button callback")
        }
        switch callbackCount {
        case 0:
            stageLabel?.stringValue = "Confirm"
            instruction?.stringValue = "Confirm the local test action."
            button.title = "Confirm"
        case 1:
            stageLabel?.stringValue = "Complete"
            instruction?.stringValue = "The owned fixture reached its final stage."
            finalLabel?.stringValue = "Task complete"
            finalLabel?.isHidden = false
            button.isEnabled = false
            button.isHidden = true
        default:
            fail("More than two native action callbacks")
        }
        callbackCount += 1
    }

    private func scheduleCapture() {
        // Let AppKit complete the button's programmatic highlight and native redraw.
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.25) {
            do { try self.captureStage() }
            catch { fail("Collection failed: \(error)") }
        }
    }

    private func readback(from root: NSView, pixelWidth: Int, pixelHeight: Int) -> Readback {
        // Re-query the owned content hierarchy, not the controller's step or expected values.
        func widget(_ id: String) -> NSView {
            let matches = root.subviews.filter { $0.identifier?.rawValue == id }
            guard matches.count == 1 else { fail("Missing or ambiguous native widget: \(id)") }
            return matches[0]
        }
        func text(_ id: String) -> NSTextField {
            guard let result = widget(id) as? NSTextField else { fail("Not a text widget: \(id)") }
            return result
        }
        guard let nativeButton = widget("button") as? NSButton else { fail("Not a native button") }
        let scaleX = Double(pixelWidth) / Double(root.bounds.width)
        let scaleY = Double(pixelHeight) / Double(root.bounds.height)
        var rectangles: [String: WidgetRectangle] = [:]
        for id in ["heading", "stage_label", "instruction", "button", "final_label"] {
            let view = widget(id)
            let rect = root.convert(view.bounds, from: view)
            guard root.bounds.contains(rect) else { fail("Widget outside captured view: \(id)") }
            rectangles[id] = WidgetRectangle(
                points: Rect(rect), pixels: Rect(rect, scaleX: scaleX, scaleY: scaleY),
                hidden: view.isHiddenOrHasHiddenAncestor
            )
        }
        return Readback(
            stage: text("stage_label").stringValue,
            heading: text("heading").stringValue,
            instruction: text("instruction").stringValue,
            button_title: nativeButton.title,
            button_hidden: nativeButton.isHiddenOrHasHiddenAncestor,
            button_enabled: nativeButton.isEnabled,
            final_label: text("final_label").stringValue,
            final_label_hidden: text("final_label").isHiddenOrHasHiddenAncestor,
            widget_rectangles: rectangles
        )
    }

    private func captureStage() throws {
        guard let window = window, let root = window.contentView, let button = button,
              root.isFlipped, root.bounds.origin == .zero,
              root.bounds.width > 0, root.bounds.height > 0,
              records.count < 3, callbackCount == records.count else {
            fail("Owned view or native transition invariant failed")
        }
        root.layoutSubtreeIfNeeded()
        root.displayIfNeeded()
        guard let bitmap = root.bitmapImageRepForCachingDisplay(in: root.bounds),
              bitmap.pixelsWide > 0, bitmap.pixelsHigh > 0,
              bitmap.pixelsWide <= 4096, bitmap.pixelsHigh <= 4096 else {
            fail("AppKit could not allocate a bounded native owned-view bitmap")
        }
        let observed = readback(from: root, pixelWidth: bitmap.pixelsWide, pixelHeight: bitmap.pixelsHigh)
        let expectedStages = ["Continue", "Confirm", "Complete"]
        let expectedButtons = ["Continue", "Confirm", "Confirm"]
        let final = records.count == 2
        guard observed.stage == expectedStages[records.count],
              observed.heading == "Local test workspace",
              observed.button_title == expectedButtons[records.count],
              observed.button_hidden == final, observed.button_enabled == !final,
              observed.final_label == (final ? "Task complete" : ""),
              observed.final_label_hidden == !final,
              ["heading", "stage_label", "instruction"].allSatisfy({ observed.widget_rectangles[$0]?.hidden == false }) else {
            fail("Independent AppKit readback disagrees with the required stage")
        }
        root.cacheDisplay(in: root.bounds, to: bitmap)
        guard readback(from: root, pixelWidth: bitmap.pixelsWide, pixelHeight: bitmap.pixelsHigh) == observed else {
            fail("Native widget state changed during rendering")
        }
        guard let png = bitmap.representation(using: .png, properties: [:]) else {
            fail("AppKit could not encode its native rendered view as PNG")
        }
        let filename = ["stage-01-continue.png", "stage-02-confirm.png", "stage-03-complete.png"][records.count]
        let destination = output.appendingPathComponent(filename)
        try png.write(to: destination, options: .withoutOverwriting)
        let saved = try Data(contentsOf: destination)
        guard saved == png, saved.starts(with: [137, 80, 78, 71, 13, 10, 26, 10]),
              let decoded = NSBitmapImageRep(data: saved),
              decoded.pixelsWide == bitmap.pixelsWide, decoded.pixelsHigh == bitmap.pixelsHigh else {
            fail("Written PNG readback or pixel dimensions disagree with the native bitmap")
        }
        records.append(StageRecord(
            index: records.count, stage: observed.stage.lowercased(), filename: filename,
            sha256: SHA256.hash(data: saved).map { String(format: "%02x", $0) }.joined(),
            pixel_width: decoded.pixelsWide, pixel_height: decoded.pixelsHigh,
            view_bounds_points: Rect(root.bounds),
            pixels_per_point_x: Double(decoded.pixelsWide) / Double(root.bounds.width),
            pixels_per_point_y: Double(decoded.pixelsHigh) / Double(root.bounds.height),
            trigger: records.isEmpty ? "initial_owned_window" : "NSButton.performClick(nil)",
            native_action_callback_count: callbackCount, readback: observed
        ))
        if records.count < 3 {
            button.performClick(nil)
            scheduleCapture()
        } else {
            try finish(window: window, root: root)
        }
    }

    private func finish(window: NSWindow, root: NSView) throws {
        guard records.count == 3, callbackCount == 2, Set(records.map(\.sha256)).count == 3 else {
            fail("Collector requires exactly three distinct native stage PNGs")
        }
        var system = utsname()
        guard uname(&system) == 0 else { fail("Could not read real Darwin platform metadata") }
        func value<T>(_ field: T) -> String {
            withUnsafeBytes(of: field) { bytes in
                String(decoding: bytes.prefix(while: { $0 != 0 }), as: UTF8.self)
            }
        }
        let platform = value(system.sysname)
        guard platform == "Darwin" else { fail("Native fixture collection requires real Darwin") }
        #if arch(arm64)
        let processArchitecture = "arm64"
        #elseif arch(x86_64)
        let processArchitecture = "x86_64"
        #else
        let processArchitecture = "other"
        #endif
        let version = ProcessInfo.processInfo.operatingSystemVersion
        let manifest = Manifest(
            schema_version: 1, fixture_kind: "native_owned_view_decision_fixture",
            platform: platform, os_name: "macOS",
            os_version: ProcessInfo.processInfo.operatingSystemVersionString,
            os_version_components: ["major": version.majorVersion, "minor": version.minorVersion, "patch": version.patchVersion],
            architecture: value(system.machine), process_architecture: processArchitecture,
            darwin_kernel_release: value(system.release),
            capture_method: "NSView.cacheDisplay(in:to:) -> NSBitmapImageRep.representation(using:.png)",
            capture_scope: "native owned-view rendering; NSWindow content view only; NOT an OS screenshot",
            transition_method: "NSButton.performClick(nil) -> native AppKit target/action callbacks; NOT OS input",
            readback_method: "Independent AppKit property reads via NSWindow.contentView widget identifiers before and after rendering",
            native_input: false, os_screenshot: false, desktop_e2e: false, task_e2e: false,
            model_inference: false, appearance: root.effectiveAppearance.name.rawValue,
            window_backing_scale_factor: Double(window.backingScaleFactor),
            coordinate_convention: [
                "origin": "top_left", "x_direction": "right", "y_direction": "down",
                "rect_format": "x,y,width,height",
                "points_space": "flipped NSWindow content view bounds; AppKit points",
                "pixels_space": "PNG pixels; per-axis decoded pixel dimension / view point dimension",
                "screen_coordinates": "not provided; no OS input coordinate mapping"
            ],
            collector_timeout_seconds: timeoutSeconds, stage_count: records.count, stages: records
        )
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
        let destination = output.appendingPathComponent("manifest.json")
        try encoder.encode(manifest).write(to: destination, options: .withoutOverwriting)
        let saved = try JSONDecoder().decode(Manifest.self, from: Data(contentsOf: destination))
        guard saved == manifest else { fail("Written manifest failed independent file readback") }
        for record in saved.stages {
            let png = try Data(contentsOf: output.appendingPathComponent(record.filename))
            let hash = SHA256.hash(data: png).map { String(format: "%02x", $0) }.joined()
            guard hash == record.sha256 else { fail("Final PNG SHA256 verification failed") }
        }
        window.orderOut(nil)
        watchdog.cancel()
        print("Collected 3 native owned-view decision fixture PNGs and manifest.json at \(output.path).")
        print("Scope: native owned-view rendering; native_input=false; NOT OS screenshots or desktop/task E2E.")
        exit(EXIT_SUCCESS)
    }
}

private let watchdog = DispatchSource.makeTimerSource(queue: .global(qos: .userInitiated))
watchdog.schedule(deadline: .now() + .seconds(timeoutSeconds))
watchdog.setEventHandler { fail("45-second collection deadline exceeded; partial output is not a complete fixture") }
watchdog.resume()
guard CommandLine.arguments.count == 2 else { fail("Usage: macos_decision_fixture.swift <fresh-output-directory>") }
guard Thread.isMainThread else { fail("AppKit collector must run on the main thread") }
let output = URL(fileURLWithPath: CommandLine.arguments[1], isDirectory: true).standardizedFileURL
// Atomic mkdir refuses existing directories, files, and even dangling symlinks; never clean/reuse them.
guard mkdir(output.path, mode_t(0o700)) == 0 else {
    let reason = String(cString: strerror(errno))
    fail("Refusing to reuse or overwrite output path \(output.path): \(reason); supply a fresh directory with an existing parent")
}
MainActor.assumeIsolated {
    autoreleasepool {
        let app = NSApplication.shared
        let collector = Collector(output: output)
        guard app.setActivationPolicy(.accessory) else {
            fail("AppKit refused the owned fixture activation policy")
        }
        app.delegate = collector
        withExtendedLifetime(collector) { app.run() }
        fail("AppKit event loop ended before complete fixture collection")
    }
}
#else
import Foundation
fputs("NOT_RUN: macos_decision_fixture.swift requires real Darwin/AppKit; no fixtures generated\n", stderr)
exit(EXIT_FAILURE)
#endif
