import AppKit
import Foundation
import Darwin

let home = URL(fileURLWithPath: CommandLine.arguments[1])
let appURL = URL(fileURLWithPath: CommandLine.arguments[2])
let logs = home.appendingPathComponent("logs")
try? FileManager.default.createDirectory(at: logs, withIntermediateDirectories: true)
let lockFD = open(logs.appendingPathComponent("menu.lock").path, O_CREAT | O_RDWR, mode_t(0o600))
if lockFD < 0 || flock(lockFD, LOCK_EX | LOCK_NB) != 0 { exit(0) }

class StatusMenu: NSObject {
    let item = NSStatusBar.system.statusItem(withLength: NSStatusItem.variableLength)
    let summary = NSMenuItem(title: "Athena iniciando…", action: nil, keyEquivalent: "")
    let microphone = NSMenuItem(title: "Ativar escuta ambiente", action: #selector(toggleMic), keyEquivalent: "")
    var micOn = false
    override init() {
        super.init()
        item.button?.title = "◉ A"
        let menu = NSMenu()
        menu.addItem(summary); menu.addItem(NSMenuItem.separator())
        let openItem = NSMenuItem(title: "Abrir Athena", action: #selector(openApp), keyEquivalent: "")
        openItem.target = self; menu.addItem(openItem)
        microphone.target = self; menu.addItem(microphone)
        for (title, action) in [("Parar voz", #selector(stopVoice)), ("Pausar Athena", #selector(pause)), ("Retomar Athena", #selector(resume)), ("Abrir pasta de dados", #selector(openData))] {
            let entry = NSMenuItem(title: title, action: action, keyEquivalent: "")
            entry.target = self; menu.addItem(entry)
        }
        menu.addItem(NSMenuItem.separator())
        let quit = NSMenuItem(title: "Fechar só este ícone", action: #selector(quitMenu), keyEquivalent: "")
        quit.target = self; menu.addItem(quit)
        item.menu = menu
        Timer.scheduledTimer(withTimeInterval: 1, repeats: true) { _ in self.refresh() }
        refresh()
    }
    func refresh() {
        guard let data = try? Data(contentsOf: logs.appendingPathComponent("presence-status.json")),
              let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
              let updated = json["updated"] as? Double,
              Date().timeIntervalSince1970 - updated < 20 else {
            summary.title = "Athena sem sinal recente"; item.button?.title = "◌ A"; return
        }
        let state = json["state"] as? String ?? "ativa"
        micOn = json["listening_enabled"] as? Bool ?? false
        summary.title = "Athena · " + state
        microphone.title = micOn ? "Pausar escuta ambiente" : "Ativar escuta ambiente"
        item.button?.title = micOn ? "◉ A •" : "◉ A"
        item.button?.toolTip = "Athena · " + state
    }
    func command(_ value: String) {
        let json: [String: Any] = ["command": value, "created": Date().timeIntervalSince1970]
        if let data = try? JSONSerialization.data(withJSONObject: json) {
            try? data.write(to: logs.appendingPathComponent("status-command.json"), options: .atomic)
        }
    }
    @objc func openApp() { NSWorkspace.shared.openApplication(at: appURL, configuration: NSWorkspace.OpenConfiguration()) }
    @objc func openData() { NSWorkspace.shared.open(home) }
    @objc func toggleMic() { command(micOn ? "microphone_off" : "microphone_on") }
    @objc func stopVoice() { command("stop_voice") }
    @objc func pause() { command("pause") }
    @objc func resume() { command("resume") }
    @objc func quitMenu() { NSApp.terminate(nil) }
}
let application = NSApplication.shared
application.setActivationPolicy(.accessory)
let status = StatusMenu()
application.run()
