import UIKit

/// Shared Q4 palette. Decoration never carries meaning or sits behind reading surfaces.
enum BrandTheme {
    static let page = color(light: 0xf3f1e7, dark: 0x11170f)
    static let panel = color(light: 0xfffef8, dark: 0x1c2419)
    static let ink = color(light: 0x20281e, dark: 0xf0f3e9)
    static let muted = color(light: 0x53604b, dark: 0xb8c3ab, strengthen: true)
    static let control = color(light: 0x72806a, dark: 0x879575, strengthen: true)
    static let patchA = color(light: 0xe1e4d3, dark: 0x172012)
    static let patchB = color(light: 0xdce1ce, dark: 0x222c1b)
    static let patchC = color(light: 0xe3ddc8, dark: 0x2b3321)
    static let patternOpacity: CGFloat = 0.3

    private static func rgb(_ value: UInt32) -> UIColor {
        UIColor(red: CGFloat((value >> 16) & 255) / 255,
                green: CGFloat((value >> 8) & 255) / 255,
                blue: CGFloat(value & 255) / 255, alpha: 1)
    }
    private static func color(light: UInt32, dark: UInt32, strengthen: Bool = false) -> UIColor {
        UIColor { traits in
            let darkMode = traits.userInterfaceStyle == .dark
            if strengthen && traits.accessibilityContrast == .high {
                return rgb(darkMode ? 0xf0f3e9 : 0x20281e)
            }
            return rgb(darkMode ? dark : light)
        }
    }
    static func font(_ style: UIFont.TextStyle) -> UIFont {
        let original = UIFont.preferredFont(forTextStyle: style)
        return original.fontDescriptor.withDesign(.rounded).map { UIFont(descriptor: $0, size: 0) } ?? original
    }
    static func button(_ title: String, primary: Bool = false) -> UIButton.Configuration {
        var configuration: UIButton.Configuration = primary ? .filled() : .plain()
        configuration.title = title; configuration.cornerStyle = .large
        configuration.titleLineBreakMode = .byWordWrapping
        configuration.contentInsets = NSDirectionalEdgeInsets(top: 12, leading: 16, bottom: 12, trailing: 16)
        configuration.baseForegroundColor = primary ? panel : ink
        configuration.baseBackgroundColor = primary ? ink : panel
        configuration.background.backgroundColor = primary ? ink : panel
        if !primary {
            configuration.background.strokeColor = control
            configuration.background.strokeWidth = 1
        }
        configuration.titleTextAttributesTransformer = UIConfigurationTextAttributesTransformer { attributes in
            var attributes = attributes; attributes.font = font(.headline)
            attributes.foregroundColor = primary ? panel : ink
            return attributes
        }
        return configuration
    }
    static func installBackdrop(in view: UIView) {
        view.backgroundColor = page; view.tintColor = ink
        let backdrop = BrandBackdropView(); backdrop.translatesAutoresizingMaskIntoConstraints = false
        view.insertSubview(backdrop, at: 0)
        NSLayoutConstraint.activate([
            backdrop.topAnchor.constraint(equalTo: view.topAnchor),
            backdrop.bottomAnchor.constraint(equalTo: view.bottomAnchor),
            backdrop.leadingAnchor.constraint(equalTo: view.leadingAnchor),
            backdrop.trailingAnchor.constraint(equalTo: view.trailingAnchor)
        ])
    }
}

/// Same fixed organic paths as camo-q4.svg; no images, network, motion or touch handling.
private final class BrandBackdropView: UIView {
    private var observers: [NSObjectProtocol] = []
    override init(frame: CGRect) { super.init(frame: frame); configure() }
    required init?(coder: NSCoder) { super.init(coder: coder); configure() }
    private func configure() {
        isUserInteractionEnabled = false; isAccessibilityElement = false
        accessibilityElementsHidden = true; isOpaque = true; contentMode = .redraw
        registerForTraitChanges([UITraitUserInterfaceStyle.self, UITraitAccessibilityContrast.self],
            target: self, action: #selector(refreshAppearance))
        observers.append(NotificationCenter.default.addObserver(
            forName: UIAccessibility.reduceTransparencyStatusDidChangeNotification,
            object: nil, queue: .main) { [weak self] _ in self?.setNeedsDisplay() })
    }
    deinit { for observer in observers { NotificationCenter.default.removeObserver(observer) } }
    @objc private func refreshAppearance() { setNeedsDisplay() }
    override func draw(_ rect: CGRect) {
        BrandTheme.page.resolvedColor(with: traitCollection).setFill(); UIRectFill(bounds)
        guard traitCollection.accessibilityContrast != .high,
              !UIAccessibility.isReduceTransparencyEnabled,
              let context = UIGraphicsGetCurrentContext() else { return }
        let colors = [BrandTheme.patchA, BrandTheme.patchB, BrandTheme.patchC]
        for y in stride(from: CGFloat(0), to: bounds.height, by: 320) {
            for x in stride(from: CGFloat(0), to: bounds.width, by: 480) {
                context.saveGState(); context.translateBy(x: x, y: y)
                for (index, path) in Self.paths.enumerated() {
                    colors[index].resolvedColor(with: traitCollection)
                        .withAlphaComponent(BrandTheme.patternOpacity).setFill()
                    path.fill()
                }
                context.restoreGState()
            }
        }
    }
    private static let paths: [UIBezierPath] = [
    {
        let path = UIBezierPath()
        path.move(to: CGPoint(x: -35, y: 27))
        path.addCurve(to: CGPoint(x: 81, y: 13), controlPoint1: CGPoint(x: 2, y: -13), controlPoint2: CGPoint(x: 48, y: -5))
        path.addCurve(to: CGPoint(x: 126, y: 61), controlPoint1: CGPoint(x: 107, y: 28), controlPoint2: CGPoint(x: 93, y: 51))
        path.addCurve(to: CGPoint(x: 217, y: 82), controlPoint1: CGPoint(x: 159, y: 72), controlPoint2: CGPoint(x: 195, y: 56))
        path.addCurve(to: CGPoint(x: 181, y: 121), controlPoint1: CGPoint(x: 234, y: 103), controlPoint2: CGPoint(x: 215, y: 122))
        path.addCurve(to: CGPoint(x: 108, y: 151), controlPoint1: CGPoint(x: 143, y: 120), controlPoint2: CGPoint(x: 139, y: 145))
        path.addCurve(to: CGPoint(x: 15, y: 133), controlPoint1: CGPoint(x: 70, y: 158), controlPoint2: CGPoint(x: 47, y: 122))
        path.addCurve(to: CGPoint(x: -35, y: 95), controlPoint1: CGPoint(x: -12, y: 143), controlPoint2: CGPoint(x: -44, y: 122))
        path.close()
        path.move(to: CGPoint(x: 306, y: 184))
        path.addCurve(to: CGPoint(x: 383, y: 151), controlPoint1: CGPoint(x: 329, y: 161), controlPoint2: CGPoint(x: 361, y: 169))
        path.addCurve(to: CGPoint(x: 446, y: 171), controlPoint1: CGPoint(x: 408, y: 129), controlPoint2: CGPoint(x: 449, y: 144))
        path.addCurve(to: CGPoint(x: 501, y: 226), controlPoint1: CGPoint(x: 443, y: 201), controlPoint2: CGPoint(x: 489, y: 200))
        path.addCurve(to: CGPoint(x: 449, y: 274), controlPoint1: CGPoint(x: 514, y: 257), controlPoint2: CGPoint(x: 479, y: 281))
        path.addCurve(to: CGPoint(x: 361, y: 285), controlPoint1: CGPoint(x: 414, y: 265), controlPoint2: CGPoint(x: 395, y: 298))
        path.addCurve(to: CGPoint(x: 319, y: 228), controlPoint1: CGPoint(x: 326, y: 271), controlPoint2: CGPoint(x: 343, y: 240))
        path.addCurve(to: CGPoint(x: 306, y: 184), controlPoint1: CGPoint(x: 299, y: 218), controlPoint2: CGPoint(x: 290, y: 201))
        path.close()
        return path
    }(),
    {
        let path = UIBezierPath()
        path.move(to: CGPoint(x: 262, y: -24))
        path.addCurve(to: CGPoint(x: 305, y: 31), controlPoint1: CGPoint(x: 291, y: -14), controlPoint2: CGPoint(x: 280, y: 20))
        path.addCurve(to: CGPoint(x: 376, y: 43), controlPoint1: CGPoint(x: 329, y: 41), controlPoint2: CGPoint(x: 358, y: 27))
        path.addCurve(to: CGPoint(x: 355, y: 88), controlPoint1: CGPoint(x: 402, y: 66), controlPoint2: CGPoint(x: 383, y: 88))
        path.addCurve(to: CGPoint(x: 297, y: 123), controlPoint1: CGPoint(x: 329, y: 88), controlPoint2: CGPoint(x: 325, y: 119))
        path.addCurve(to: CGPoint(x: 228, y: 109), controlPoint1: CGPoint(x: 263, y: 127), controlPoint2: CGPoint(x: 255, y: 101))
        path.addCurve(to: CGPoint(x: 179, y: 70), controlPoint1: CGPoint(x: 198, y: 117), controlPoint2: CGPoint(x: 171, y: 95))
        path.addCurve(to: CGPoint(x: 228, y: 25), controlPoint1: CGPoint(x: 187, y: 44), controlPoint2: CGPoint(x: 221, y: 52))
        path.addCurve(to: CGPoint(x: 262, y: -24), controlPoint1: CGPoint(x: 235, y: 1), controlPoint2: CGPoint(x: 233, y: -34))
        path.close()
        path.move(to: CGPoint(x: -23, y: 231))
        path.addCurve(to: CGPoint(x: 53, y: 202), controlPoint1: CGPoint(x: 4, y: 206), controlPoint2: CGPoint(x: 33, y: 223))
        path.addCurve(to: CGPoint(x: 110, y: 211), controlPoint1: CGPoint(x: 74, y: 181), controlPoint2: CGPoint(x: 100, y: 188))
        path.addCurve(to: CGPoint(x: 172, y: 237), controlPoint1: CGPoint(x: 120, y: 235), controlPoint2: CGPoint(x: 150, y: 223))
        path.addCurve(to: CGPoint(x: 160, y: 293), controlPoint1: CGPoint(x: 199, y: 254), controlPoint2: CGPoint(x: 189, y: 287))
        path.addCurve(to: CGPoint(x: 89, y: 301), controlPoint1: CGPoint(x: 127, y: 300), controlPoint2: CGPoint(x: 111, y: 279))
        path.addCurve(to: CGPoint(x: 21, y: 306), controlPoint1: CGPoint(x: 67, y: 325), controlPoint2: CGPoint(x: 40, y: 325))
        path.addCurve(to: CGPoint(x: -23, y: 231), controlPoint1: CGPoint(x: 4, y: 289), controlPoint2: CGPoint(x: -43, y: 271))
        path.close()
        return path
    }(),
    {
        let path = UIBezierPath()
        path.move(to: CGPoint(x: 165, y: 151))
        path.addCurve(to: CGPoint(x: 215, y: 134), controlPoint1: CGPoint(x: 180, y: 142), controlPoint2: CGPoint(x: 203, y: 147))
        path.addCurve(to: CGPoint(x: 267, y: 145), controlPoint1: CGPoint(x: 235, y: 111), controlPoint2: CGPoint(x: 266, y: 121))
        path.addCurve(to: CGPoint(x: 299, y: 182), controlPoint1: CGPoint(x: 268, y: 165), controlPoint2: CGPoint(x: 296, y: 160))
        path.addCurve(to: CGPoint(x: 259, y: 231), controlPoint1: CGPoint(x: 302, y: 207), controlPoint2: CGPoint(x: 270, y: 213))
        path.addCurve(to: CGPoint(x: 207, y: 228), controlPoint1: CGPoint(x: 246, y: 252), controlPoint2: CGPoint(x: 214, y: 248))
        path.addCurve(to: CGPoint(x: 153, y: 195), controlPoint1: CGPoint(x: 199, y: 204), controlPoint2: CGPoint(x: 165, y: 216))
        path.addCurve(to: CGPoint(x: 165, y: 151), controlPoint1: CGPoint(x: 143, y: 178), controlPoint2: CGPoint(x: 146, y: 163))
        path.close()
        path.move(to: CGPoint(x: 410, y: -18))
        path.addCurve(to: CGPoint(x: 455, y: 21), controlPoint1: CGPoint(x: 433, y: -10), controlPoint2: CGPoint(x: 431, y: 18))
        path.addCurve(to: CGPoint(x: 519, y: 30), controlPoint1: CGPoint(x: 484, y: 25), controlPoint2: CGPoint(x: 508, y: 6))
        path.addCurve(to: CGPoint(x: 487, y: 74), controlPoint1: CGPoint(x: 530, y: 55), controlPoint2: CGPoint(x: 509, y: 70))
        path.addCurve(to: CGPoint(x: 432, y: 90), controlPoint1: CGPoint(x: 462, y: 78), controlPoint2: CGPoint(x: 453, y: 100))
        path.addCurve(to: CGPoint(x: 403, y: 50), controlPoint1: CGPoint(x: 412, y: 80), controlPoint2: CGPoint(x: 420, y: 58))
        path.addCurve(to: CGPoint(x: 410, y: -18), controlPoint1: CGPoint(x: 383, y: 40), controlPoint2: CGPoint(x: 386, y: -26))
        path.close()
        return path
    }()
    ]
}
