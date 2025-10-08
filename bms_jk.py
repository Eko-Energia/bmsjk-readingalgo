import serial
import time


def jk_bms_protocol_analyzer():
    print("🔍 JK BMS - ANALIZATOR PROTOKOŁU")
    print("=" * 50)

    port = "COM28"
    baud = 115200

    # Komendy do testowania
    commands = {
        "SOC": "4E57001300000000030300850000000068000001AB",
        "Voltage": "4E57001300000000030300830000000068000001A9",
        "Current": "4E57001300000000030300840000000068000001AA",
        "Temperature": "4E57001300000000030300810000000068000001A7",
        "Capacity": "4E57001300000000030300AA0000000068000001D0",
    }

    try:
        ser = serial.Serial(port, baud, timeout=1, write_timeout=1)
        print(f"📡 Połączono z BMS")
        print("-" * 60)

        for name, cmd_hex in commands.items():
            print(f"\n🎯 {name}:")

            ser.reset_input_buffer()
            ser.write(bytes.fromhex(cmd_hex))
            time.sleep(0.5)

            if ser.in_waiting > 0:
                response = ser.read(ser.in_waiting)

                if response[:2] == b"\x4e\x57":  # Ramka JK
                    print(f"   📦 Odebrano: {len(response)} bajtów")
                    print(f"   🔢 HEX: {response.hex().upper()}")

                    # Pokazuj strukturę ramki
                    print(f"   🏗️  Struktura ramki:")
                    for i in range(0, len(response), 8):
                        line = ""
                        for j in range(8):
                            if i + j < len(response):
                                byte = response[i + j]
                                marker = " "
                                if i + j == 10:
                                    marker = "Ⓣ"  # Typ?
                                elif i + j >= 11 and i + j <= 14:
                                    marker = "Ⓓ"  # Dane?
                                line += f"[{i+j:2d}]0x{byte:02X}{marker} "
                        if line:
                            print(f"      {line}")

                else:
                    print(f"   ❌ Nieprawidłowa ramka JK")

            else:
                print(f"   ⚠️  Brak odpowiedzi")

        ser.close()

    except Exception as e:
        print(f"💥 Błąd: {e}")


def find_data_in_frame(response, param_name):
    """Znajduje dane w ramce odpowiedzi"""
    if len(response) < 12:
        return None

    # Przeszukaj różne pozycje w ramce
    search_positions = [
        (10, 1, "1B"),  # Pozycja 10, 1 bajt
        (11, 1, "1B"),  # Pozycja 11, 1 bajt
        (12, 1, "1B"),  # Pozycja 12, 1 bajt
        (10, 2, "2B"),  # Pozycja 10, 2 bajty
        (11, 2, "2B"),  # Pozycja 11, 2 bajty
        (12, 2, "2B"),  # Pozycja 12, 2 bajty
        (13, 2, "2B"),  # Pozycja 13, 2 bajty
        (11, 4, "4B"),  # Pozycja 11, 4 bajty
    ]

    for pos, length, desc in search_positions:
        if pos + length <= len(response):
            data_bytes = response[pos : pos + length]

            if param_name == "SOC" and length == 1:
                value = data_bytes[0]
                if 0 <= value <= 100:  # SOC musi być 0-100%
                    return pos, f"{value}%", data_bytes

            elif param_name == "Voltage" and length == 2:
                raw = (data_bytes[0] << 8) + data_bytes[1]
                voltage = raw * 0.01
                if 20 <= voltage <= 30:  # Napięcie LiFePO4
                    return pos, f"{voltage:.2f}V", data_bytes

            elif param_name == "Current" and length == 2:
                raw = (data_bytes[0] << 8) + data_bytes[1]
                if raw & 0x8000:
                    raw = raw - 65536  # Signed
                current = raw * 0.01
                if -100 <= current <= 100:  # Prąd w rozsądnym zakresie
                    direction = "↗️" if current < 0 else "↘️" if current > 0 else "⏸️"
                    return pos, f"{current:+.2f}A {direction}", data_bytes

            elif param_name == "Temperature" and length == 2:
                raw = (data_bytes[0] << 8) + data_bytes[1]
                if -20 <= raw <= 100:  # Temperatura
                    return pos, f"{raw}°C", data_bytes

            elif param_name == "Capacity" and length == 4:
                raw = (
                    (data_bytes[0] << 24)
                    + (data_bytes[1] << 16)
                    + (data_bytes[2] << 8)
                    + data_bytes[3]
                )
                if 0 <= raw <= 1000:  # Pojemność w Ah
                    return pos, f"{raw}Ah", data_bytes

    return None


def jk_bms_data_mapper():
    """Mapuje gdzie są jakie dane w ramkach"""
    print("\n🗺️  MAPOWANIE DANYCH W RAMKACH")
    print("=" * 50)

    port = "COM28"
    baud = 115200

    commands = {
        "SOC": "4E57001300000000030300850000000068000001AB",
        "Voltage": "4E57001300000000030300830000000068000001A9",
        "Current": "4E57001300000000030300840000000068000001AA",
    }

    try:
        ser = serial.Serial(port, baud, timeout=1, write_timeout=1)

        print("📊 Odkrywanie pozycji danych:")
        print("-" * 45)

        data_map = {}

        for name, cmd_hex in commands.items():
            ser.reset_input_buffer()
            ser.write(bytes.fromhex(cmd_hex))
            time.sleep(0.5)

            if ser.in_waiting > 0:
                response = ser.read(ser.in_waiting)

                if response[:2] == b"\x4e\x57":
                    # Szukaj danych
                    found = find_data_in_frame(response, name)
                    if found:
                        pos, value, bytes_data = found
                        data_map[name] = {
                            "position": pos,
                            "length": len(bytes_data),
                            "value": value,
                            "bytes": bytes_data.hex().upper(),
                        }
                        print(f"✅ {name}:")
                        print(f"   📍 Pozycja: {pos}")
                        print(f"   📏 Długość: {len(bytes_data)} bajtów")
                        print(f"   💾 Bajty: {bytes_data.hex().upper()}")
                        print(f"   💡 Wartość: {value}")
                    else:
                        print(f"❌ {name}: Nie znaleziono danych")

        # Podsumowanie mapowania
        if data_map:
            print(f"\n🎯 MAPA DANYCH:")
            print("-" * 35)
            for name, info in data_map.items():
                print(f"   {name}:")
                print(f"      → Pozycja: {info['position']}")
                print(f"      → Długość: {info['length']}B")
                print(f"      → Wartość: {info['value']}")
                print(f"      → HEX: {info['bytes']}")

        ser.close()

    except Exception as e:
        print(f"💥 Błąd: {e}")


# Uruchom analizę
if __name__ == "__main__":
    jk_bms_protocol_analyzer()
    jk_bms_data_mapper()
