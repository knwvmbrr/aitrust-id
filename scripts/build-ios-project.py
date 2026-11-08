#!/usr/bin/env python3
"""Prepare an unreleased developer Xcode project; no phone signing or release claim."""
import argparse
import hashlib
import json
import io
from pathlib import Path
import plistlib
import runpy
import sys
import zipfile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = ROOT
sys.path.insert(0, str(ROOT))
from tools.blind_review_io import create, PacketError


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def uid(name):
    return digest(name.encode())[:24].upper()


def project():
    objects = {}
    def put(identity, isa, **fields):
        key = uid(identity); objects[key] = {"isa": isa, **fields}; return key
    source_refs = {name: put('file-' + name, 'PBXFileReference', lastKnownFileType='sourcecode.swift', path=name, sourceTree='<group>')
                   for name in ['App.swift', 'Assets.swift', 'CheckerController.swift', 'ShareController.swift', 'SharedText.swift']}
    sources = put('source-group', 'PBXGroup', children=list(source_refs.values()), path='Source', sourceTree='<group>')
    assets = put('assets-folder', 'PBXFileReference', lastKnownFileType='folder', path='Assets', sourceTree='<group>')
    products = {}
    for target, suffix, kind in [('App', 'app', 'wrapper.application'), ('Share', 'appex', 'wrapper.app-extension')]:
        products[target] = put('product-' + target, 'PBXFileReference', explicitFileType=kind, path='AITrustID' + ('Share' if target == 'Share' else '') + '.' + suffix, sourceTree='BUILT_PRODUCTS_DIR')
    product_group = put('product-group', 'PBXGroup', children=list(products.values()), name='Products', sourceTree='<group>')
    test_file = put('ui-file', 'PBXFileReference', lastKnownFileType='sourcecode.swift', path='UIFlows.swift', sourceTree='<group>')
    tests = put('test-group', 'PBXGroup', children=[test_file], path='Tests', sourceTree='<group>')
    group = put('main-group', 'PBXGroup', children=[sources, tests, assets, product_group], sourceTree='<group>')
    targets = {}
    for target, main in [('App', 'App.swift'), ('Share', 'ShareController.swift')]:
        build_files = [put(target + '-source-' + name, 'PBXBuildFile', fileRef=source_refs[name]) for name in [main, 'Assets.swift', 'CheckerController.swift', 'SharedText.swift']]
        phases = [put(target + '-sources', 'PBXSourcesBuildPhase', buildActionMask=2147483647, files=build_files, runOnlyForDeploymentPostprocessing=0),
                  put(target + '-resources', 'PBXResourcesBuildPhase', buildActionMask=2147483647, files=[put(target + '-asset-build', 'PBXBuildFile', fileRef=assets)], runOnlyForDeploymentPostprocessing=0)]
        if target == 'App':
            embedded = put('embed-share-build', 'PBXBuildFile', fileRef=products['Share'], settings={'ATTRIBUTES': ['CodeSignOnCopy', 'RemoveHeadersOnCopy']})
            phases.append(put('embed-share', 'PBXCopyFilesBuildPhase', buildActionMask=2147483647, dstPath='', dstSubfolderSpec=13, files=[embedded], name='Embed Share Extension', runOnlyForDeploymentPostprocessing=0))
        configurations = []
        for mode in ['Debug', 'Release']:
            settings = {'PRODUCT_NAME': 'AITrustID' + ('Share' if target == 'Share' else ''), 'PRODUCT_BUNDLE_IDENTIFIER': 'com.aitrustid.personal.preview' + ('.share' if target == 'Share' else ''),
                        'INFOPLIST_FILE': target + '-Info.plist', 'GENERATE_INFOPLIST_FILE': 'NO', 'CODE_SIGNING_ALLOWED': 'NO', 'SWIFT_VERSION': '5.0',
                        'IPHONEOS_DEPLOYMENT_TARGET': '18.0', 'TARGETED_DEVICE_FAMILY': '1,2', 'SUPPORTED_PLATFORMS': 'iphoneos iphonesimulator',
                        'LD_RUNPATH_SEARCH_PATHS': '$(inherited) @executable_path/Frameworks @executable_path/../../Frameworks', 'SWIFT_OPTIMIZATION_LEVEL': '-Onone' if mode == 'Debug' else '-O'}
            if target == 'Share': settings.update(APPLICATION_EXTENSION_API_ONLY='YES', SKIP_INSTALL='YES')
            configurations.append(put(target + '-config-' + mode, 'XCBuildConfiguration', buildSettings=settings, name=mode))
        configuration_list = put(target + '-configuration-list', 'XCConfigurationList', buildConfigurations=configurations, defaultConfigurationIsVisible=0, defaultConfigurationName='Debug')
        targets[target] = put('target-' + target, 'PBXNativeTarget', buildConfigurationList=configuration_list, buildPhases=phases, buildRules=[], dependencies=[], name='AITrustID' + ('Share' if target == 'Share' else ''), productName='AITrustID' + ('Share' if target == 'Share' else ''), productReference=products[target], productType='com.apple.product-type.application' if target == 'App' else 'com.apple.product-type.app-extension')
    proxy = put('share-proxy', 'PBXContainerItemProxy', containerPortal=uid('project'), proxyType=1, remoteGlobalIDString=targets['Share'], remoteInfo='AITrustIDShare')
    dependency = put('share-dependency', 'PBXTargetDependency', target=targets['Share'], targetProxy=proxy)
    objects[targets['App']]['dependencies'] = [dependency]
    ui_product = put('product-ui', 'PBXFileReference', explicitFileType='wrapper.cfbundle', path='AITrustIDUITests.xctest', sourceTree='BUILT_PRODUCTS_DIR')
    objects[product_group]['children'].append(ui_product)
    ui_source = put('ui-source-build', 'PBXBuildFile', fileRef=test_file)
    ui_phase = put('ui-source-phase', 'PBXSourcesBuildPhase', buildActionMask=2147483647, files=[ui_source], runOnlyForDeploymentPostprocessing=0)
    ui_configs = [put('ui-config-' + mode, 'XCBuildConfiguration', name=mode, buildSettings={'PRODUCT_NAME': 'AITrustIDUITests', 'PRODUCT_BUNDLE_IDENTIFIER': 'com.aitrustid.personal.preview.uiTests', 'GENERATE_INFOPLIST_FILE': 'YES', 'TEST_TARGET_NAME': 'AITrustID', 'SWIFT_VERSION': '5.0', 'IPHONEOS_DEPLOYMENT_TARGET': '18.0', 'TARGETED_DEVICE_FAMILY': '1,2', 'CODE_SIGNING_ALLOWED': 'NO', 'LD_RUNPATH_SEARCH_PATHS': '$(inherited) @executable_path/Frameworks @loader_path/Frameworks'}) for mode in ['Debug', 'Release']]
    ui_config_list = put('ui-config-list', 'XCConfigurationList', buildConfigurations=ui_configs, defaultConfigurationIsVisible=0, defaultConfigurationName='Debug')
    app_proxy = put('ui-app-proxy', 'PBXContainerItemProxy', containerPortal=uid('project'), proxyType=1, remoteGlobalIDString=targets['App'], remoteInfo='AITrustID')
    ui_dependency = put('ui-app-dependency', 'PBXTargetDependency', target=targets['App'], targetProxy=app_proxy)
    targets['UI'] = put('target-UI', 'PBXNativeTarget', name='AITrustIDUITests', productName='AITrustIDUITests', productType='com.apple.product-type.bundle.ui-testing', productReference=ui_product, buildConfigurationList=ui_config_list, buildPhases=[ui_phase], buildRules=[], dependencies=[ui_dependency])
    project_configs = [put('project-config-' + mode, 'XCBuildConfiguration', buildSettings={'SDKROOT': 'iphoneos', 'CLANG_ENABLE_MODULES': 'YES'}, name=mode) for mode in ['Debug', 'Release']]
    config = put('project-config-list', 'XCConfigurationList', buildConfigurations=project_configs, defaultConfigurationIsVisible=0, defaultConfigurationName='Debug')
    project_key = put('project', 'PBXProject', attributes={'LastUpgradeCheck': '1600'}, buildConfigurationList=config, compatibilityVersion='Xcode 14.0', developmentRegion='en', hasScannedForEncodings=0, knownRegions=['en', 'Base'], mainGroup=group, productRefGroup=product_group, projectDirPath='', projectRoot='', targets=list(targets.values()))
    return {'archiveVersion': '1', 'classes': {}, 'objectVersion': '56', 'objects': objects, 'rootObject': project_key}


def scheme():
    root = ET.Element('Scheme', LastUpgradeVersion='1600', version='1.3')
    action = ET.SubElement(root, 'BuildAction', parallelizeBuildables='YES', buildImplicitDependencies='YES')
    entries = ET.SubElement(action, 'BuildActionEntries')
    def reference(parent, target, product, name):
        ET.SubElement(parent, 'BuildableReference', BuildableIdentifier='primary', BlueprintIdentifier=uid('target-' + target), BuildableName=product, BlueprintName=name, ReferencedContainer='container:AITrustID.xcodeproj')
    entry = ET.SubElement(entries, 'BuildActionEntry', buildForTesting='YES', buildForRunning='YES', buildForProfiling='YES', buildForArchiving='YES', buildForAnalyzing='YES')
    reference(entry, 'App', 'AITrustID.app', 'AITrustID')
    entry = ET.SubElement(entries, 'BuildActionEntry', buildForTesting='YES', buildForRunning='NO', buildForProfiling='NO', buildForArchiving='NO', buildForAnalyzing='YES')
    reference(entry, 'UI', 'AITrustIDUITests.xctest', 'AITrustIDUITests')
    test = ET.SubElement(root, 'TestAction', buildConfiguration='Debug', selectedDebuggerIdentifier='Xcode.DebuggerFoundation.Debugger.LLDB', selectedLauncherIdentifier='Xcode.IDEFoundation.Launcher.LLDB', shouldUseLaunchSchemeArgsEnv='YES')
    testables = ET.SubElement(test, 'Testables'); testable = ET.SubElement(testables, 'TestableReference', skipped='NO')
    reference(testable, 'UI', 'AITrustIDUITests.xctest', 'AITrustIDUITests')
    launch = ET.SubElement(root, 'LaunchAction', buildConfiguration='Debug', selectedDebuggerIdentifier='Xcode.DebuggerFoundation.Debugger.LLDB', selectedLauncherIdentifier='Xcode.IDEFoundation.Launcher.LLDB', launchStyle='0', useCustomWorkingDirectory='NO', ignoresPersistentStateOnLaunch='NO', debugDocumentVersioning='YES', debugServiceExtension='internal', allowLocationSimulation='NO')
    runnable = ET.SubElement(launch, 'BuildableProductRunnable', runnableDebuggingMode='0'); reference(runnable, 'App', 'AITrustID.app', 'AITrustID')
    return ET.tostring(root, encoding='utf-8', xml_declaration=True)


def files():
    # Keep the current source/runtime/notice contract in one audited packager.
    native = runpy.run_path(str(SOURCE_ROOT / 'scripts/native_bundle.py'))
    native['assets'].__globals__['ROOT'] = ROOT
    payload = native['assets']()
    allowed = {'App.swift', 'Assets.swift', 'CheckerController.swift', 'ShareController.swift', 'SharedText.swift'}
    source = ROOT / 'mobile/ios/Source'
    if {p.name for p in source.iterdir()} != allowed:
        raise ValueError('Unreviewed native source')
    for name in sorted(allowed):
        file = source / name
        if not file.is_file() or file.is_symlink(): raise ValueError('Source link refused')
        payload['Source/' + name] = file.read_bytes()
    file = ROOT / 'mobile/ios/Tests/UIFlows.swift'
    if not file.is_file() or file.is_symlink(): raise ValueError('Test source refused')
    payload['Tests/UIFlows.swift'] = file.read_bytes()
    for target in ['App', 'Share']:
        info = {'CFBundleDisplayName': 'AI Trust ID', 'CFBundleIdentifier': '$(PRODUCT_BUNDLE_IDENTIFIER)', 'CFBundleExecutable': '$(EXECUTABLE_NAME)', 'CFBundleName': '$(PRODUCT_NAME)',
                'CFBundlePackageType': 'APPL' if target == 'App' else 'XPC!', 'CFBundleVersion': '1', 'CFBundleShortVersionString': '0.1', 'LSRequiresIPhoneOS': True}
        if target == 'App': info.update(UILaunchScreen={}, UIApplicationSceneManifest={'UIApplicationSupportsMultipleScenes': False})
        else: info['NSExtension'] = {'NSExtensionPointIdentifier': 'com.apple.share-services', 'NSExtensionPrincipalClass': 'ShareController', 'NSExtensionAttributes': {'NSExtensionActivationRule': {'NSExtensionActivationSupportsText': True}}}
        payload[target + '-Info.plist'] = plistlib.dumps(info)
    payload['AITrustID.xcodeproj/project.pbxproj'] = plistlib.dumps(project())
    payload['AITrustID.xcodeproj/xcshareddata/xcschemes/AITrustID.xcscheme'] = scheme()
    return payload


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        payload = files()
        archive = io.BytesIO()
        with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED) as package:
            for name, raw in sorted(payload.items()):
                if Path(name).is_absolute() or any(part in ('.', '..') for part in Path(name).parts):
                    raise ValueError('Unsafe package path')
                info = zipfile.ZipInfo(name); info.external_attr = 0o100600 << 16
                package.writestr(info, raw, compress_type=zipfile.ZIP_DEFLATED)
        create(args.output, ROOT, {'AI-Trust-ID-iOS.zip': archive.getvalue()})
        print(json.dumps({'pass': True, 'public_files_written': len(payload), 'credentials_generated': False, 'phone_signing_configured': False, 'independent_accuracy_evidence': False}))
        return 0
    except (ValueError, OSError, KeyError, TypeError, PacketError):
        print('Native project unavailable: prepare current public assets and choose a new private folder outside the checkout.', file=sys.stderr); return 2


if __name__ == '__main__': raise SystemExit(main())
