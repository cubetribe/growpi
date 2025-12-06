📱 GrowPi Mobile App – Developer Guide (iOS)

Dieser Leitfaden beschreibt die Architektur, Build-Varianten, API-Anbindung und
den Workflow zur Entwicklung einer iOS-App für GrowPi. Kurz, präzise, technisch
tief genug für deinen Assistenten.

⸻

1. Zielsetzung

Die App soll: •	Sensor- und Lampen-Daten auslesen (/api/status, /api/logs/...).
•	Lampen steuern (POST-Actions). •	Zunächst lokal gegen den Raspberry Pi
arbeiten. •	Später remote gegen den VPS (Next.js Backend + PostgreSQL).

⸻

2. iOS Developer Setup (ohne App Store) •	Xcode installieren (Mac App Store).
   •	iPhone per USB verbinden. •	In Xcode: Signing & Capabilities →
   Automatically manage signing aktivieren. •	Apple-ID reicht aus (kein
   kostenpflichtiger Developer-Account notwendig). •	Build Target = eigenes
   iPhone → Run → App wird direkt installiert.

Einschränkung: Free-Provisioning erfordert alle paar Tage erneutes Builds.

⸻

3. Architektur der App

Empfehlung: SwiftUI + URLSession API-Client

Module:

/GrowPiApp /Models /Services /Views /Config

Clean Separation: •	Config/BaseURL.swift → Dev/Prod URLs
•	Services/ApiClient.swift → REST-Calls •	Models/* → Status, Logs, Lighting
•	Views/* → Dashboard, LampControl, Logs

⸻

4. Base-URLs (lokal vs. VPS)

#if DEBUG let BASE_URL = URL(string: "http://192.168.0.86:5000")! // Raspberry
Pi #else let BASE_URL = URL(string: "https://growpi.de")! // VPS #endif

⸻

5. Beispielmodell – Status

struct GrowStatus: Codable { let temperature: Double let humidity: Double let
soil: Double let power: Double let lamps: [LampStatus] }

struct LampStatus: Codable { let id: String let state: Bool let intensity: Int }

⸻

6. API-Client (Basis)

final class ApiClient { static let shared = ApiClient()

    func getStatus() async throws -> GrowStatus {
        let url = BASE_URL.appendingPathComponent("/api/status")
        let (data, _) = try await URLSession.shared.data(from: url)
        return try JSONDecoder().decode(GrowStatus.self, from: data)
    }

    func setLampOverride(id: String, value: Int) async throws {
        var req = URLRequest(url: BASE_URL.appendingPathComponent("/api/lighting/override"))
        req.httpMethod = "POST"
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        req.httpBody = try JSONEncoder().encode(["lamp": id, "value": value])
        _ = try await URLSession.shared.data(for: req)
    }

}

⸻

7. Beispiel-View (SwiftUI Dashboard)

struct DashboardView: View { @State private var status: GrowStatus?

    var body: some View {
        VStack {
            if let s = status {
                Text("Temp: \(s.temperature)°C")
                Text("Humidity: \(s.humidity)%")
                Text("Soil: \(s.soil)%")
            } else {
                ProgressView("Loading…")
            }
        }
        .task {
            status = try? await ApiClient.shared.getStatus()
        }
    }

}

⸻

8. Workflow des Entwicklers
   1. Clone des GrowPi Repos (lokal & VPS getrennte Branches möglich).
   2. Im Xcode neues Projekt → SwiftUI App Template.
   3. Die oben definierten Module (Config, Models, Services, Views) anlegen.
   4. Erste Funktion: GET /api/status implementieren.
   5. Dashboard anzeigen lassen (lokal gegen Pi).
   6. Switch auf VPS testen → Build Configuration umstellen.
   7. Lampensteuerung implementieren (POST /lighting/override).
   8. Logs-Abfrage folgen lassen (Pagination optional).
   9. UI verbessern (Charts, Lamp-Sliders, Dark-Mode usw.).

⸻

9. Deployment-Strategie

Development: •	App läuft lokal → iPhone → Pi-API.

Staging: •	VPS Build → iPhone über Debug-Mode → BASE_URL = https://growpi.de.

Production: •	Erst wenn du willst: •	Apple Developer Programm (99 €/Jahr)
•	TestFlight + App Store Option

Für private Nutzung ist kein App Store nötig.

⸻

10. Erweiterungen (Optional) •	Offline-Cache via AppStorage oder SQLite.
    •	WebSocket für Live-Updates (Sensorwerte in Echtzeit). •	Push-Notifications
    bei Grenzwerten (requires paid developer account). •	Automationskurven
    steuern → in UI als Graph + editable Keyframes. •	Auth mit JWT / BasicToken
    (für VPS abgesichert).
