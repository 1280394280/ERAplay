from eraplay.plugins import PluginCapability, PluginManifest, PluginPermission


def test_plugin_manifest_from_dict() -> None:
    manifest = PluginManifest.from_dict(
        {
            "id": "example.status-panel",
            "name": "Status Panel",
            "version": "0.1.0",
            "entry": "plugin.py",
            "capabilities": ["editor.panel"],
            "permissions": ["project.read"],
        }
    )

    assert manifest.id == "example.status-panel"
    assert manifest.capabilities == (PluginCapability.EDITOR_PANEL,)
    assert manifest.permissions == (PluginPermission.PROJECT_READ,)
